#!/usr/bin/env python3
"""
Script d'analyse des pages d'introduction (SC1)
Extrait les métadonnées du document et la table des matières depuis les premières pages.

Usage:
    python scripts/analyze_intro_pages.py -i data/s00125-025-06497-1.pdf -o intro_json.json
"""

from __future__ import annotations

import argparse
import json
import re
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERREUR: PyMuPDF requis. Installez avec: pip install PyMuPDF")
    exit(1)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("ATTENTION: OpenAI non disponible. Utilisez --no-llm pour un parsing basique.")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def extract_text_from_pdf_pages(pdf_path: Path, start_page: int = 1, end_page: int = 3) -> str:
    """
    Extrait le texte brut des pages spécifiées du PDF.
    
    Args:
        pdf_path: Chemin vers le PDF
        start_page: Page de début (1-indexed)
        end_page: Page de fin (1-indexed)
    
    Returns:
        Texte brut extrait
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF non trouvé : {pdf_path}")
    
    doc = fitz.open(pdf_path)
    pages_text = []
    
    # Ajuster les indices (PyMuPDF est 0-indexed)
    start_idx = max(0, start_page - 1)
    end_idx = min(len(doc), end_page)
    
    for page_num in range(start_idx, end_idx):
        page = doc[page_num]
        text = page.get_text()
        pages_text.append(f"=== PAGE {page_num + 1} ===\n{text}\n")
    
    doc.close()
    return "\n".join(pages_text)


def clean_text(text: str) -> str:
    """
    Nettoie le texte en excluant les éléments de header/footer.
    
    Args:
        text: Texte brut
    
    Returns:
        Texte nettoyé
    """
    # Exclure les copyrights et footers
    patterns_to_remove = [
        r"© The Author\(s\), under exclusive licence to Springer-Verlag GmbH.*?2025",
        r"©.*?Springer.*?2025",
    ]
    
    cleaned = text
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    return cleaned.strip()


def parse_metadata_basic(text: str) -> Dict[str, Any]:
    """
    Parse basique des métadonnées sans LLM (regex).
    
    Args:
        text: Texte extrait
    
    Returns:
        Dictionnaire de métadonnées
    """
    metadata = {}
    
    # DOI
    doi_match = re.search(r'https://doi\.org/([^/\s]+)/([^\s\)]+)', text)
    if doi_match:
        metadata['DOI'] = doi_match.group(1)
        metadata['DOI_num_editeur'] = doi_match.group(1).split('.')[-1] if '.' in doi_match.group(1) else ""
        metadata['DOI_num_doc'] = doi_match.group(2)
        metadata['lien_doi'] = f"https://doi.org/{doi_match.group(1)}/{doi_match.group(2)}"
    
    # Journal et volume
    journal_match = re.search(r'Diabetologia\s*\((\d{4})\)\s*(\d+)\s*\(Suppl\s*(\d+)\):([^–]+)–([^\s]+)', text)
    if journal_match:
        metadata['year'] = int(journal_match.group(1))
        metadata['journal'] = 'Diabetologia'
        metadata['page_interne_debut'] = journal_match.group(4).strip()
        metadata['page_interne_fin'] = journal_match.group(5).strip()
        metadata['tech_document_name'] = f"Diabetologia ({journal_match.group(1)}) {journal_match.group(2)} (Suppl {journal_match.group(3)}):{journal_match.group(4)}–{journal_match.group(5)}"
    
    # Nature du contenu
    if 'ABSTRACTS' in text:
        metadata['nature_contenu'] = 'ABSTRACTS'
    
    # Titre de l'événement
    event_match = re.search(r'(\d+st|\d+nd|\d+rd|\d+th)\s+EASD.*?Meeting.*?Diabetes', text, re.IGNORECASE | re.DOTALL)
    if event_match:
        metadata['doc_title'] = event_match.group(0).strip()
    
    # Ville et dates
    date_match = re.search(r'([^,]+),\s*([^,]+),\s*(\d{1,2})\s*-\s*(\d{1,2})\s+(\w+)\s+(\d{4})', text)
    if date_match:
        metadata['event_city'] = f"{date_match.group(1)}, {date_match.group(2)}"
        # Convertir le mois en nombre
        month_map = {
            'January': '01', 'February': '02', 'March': '03', 'April': '04',
            'May': '05', 'June': '06', 'July': '07', 'August': '08',
            'September': '09', 'October': '10', 'November': '11', 'December': '12'
        }
        month = date_match.group(5)
        month_num = month_map.get(month, '01')
        metadata['date_event_start'] = f"{date_match.group(6)}-{month_num}-{date_match.group(3).zfill(2)}"
        metadata['date_event_end'] = f"{date_match.group(6)}-{month_num}-{date_match.group(4).zfill(2)}"
    
    return metadata


def parse_table_of_contents_basic(text: str) -> Dict[str, Any]:
    """
    Parse basique de la table des matières sans LLM.
    Amélioré pour détecter correctement les sessions LBA (LBA OP, LBA SO).
    
    Args:
        text: Texte extrait
    
    Returns:
        Structure de table des matières avec sessions
    """
    sections = []
    sessions = []
    
    # Détecter les sections principales
    if 'Abstracts' in text:
        abstracts_section = {
            "name": "Abstracts",
            "level": 1,
            "subsections": []
        }
        
        # Index of Oral Presentations (exclure LBA OP)
        # Pattern amélioré pour exclure "LBA OP" et ne capturer que "OP"
        op_pattern = r'(?<!LBA\s)(?<!LBA)(OP\s+\d+)\s+(.+?)(?=\n(?:OP\s+\d+|SO\s+\d+|LBA\s+OP|LBA\s+SO|Index|Late-Breaking|$))'
        op_matches = re.findall(op_pattern, text, re.IGNORECASE | re.DOTALL)
        
        op_sessions = []
        for code, title in op_matches:
            title_clean = title.strip().replace('\n', ' ').replace('\r', ' ')
            # Nettoyer les espaces multiples
            title_clean = re.sub(r'\s+', ' ', title_clean)
            # Arrêter au prochain code de session
            title_clean = re.sub(r'\s+(OP\s+\d+|SO\s+\d+|LBA\s+OP|LBA\s+SO).*$', '', title_clean, flags=re.IGNORECASE)
            if 'WITHDRAWN' in title_clean.upper():
                title_clean = 'WITHDRAWN'
            op_sessions.append({
                "code": code.strip(),
                "title": title_clean
            })
            sessions.append({
                "code": code.strip(),
                "title": title_clean,
                "section": "Abstracts",
                "subsection": "Index of Oral Presentations"
            })
        
        if op_sessions:
            abstracts_section["subsections"].append({
                "name": "Index of Oral Presentations",
                "level": 2,
                "sessions": op_sessions
            })
        
        # Index of Short Oral Discussions (exclure LBA SO)
        so_pattern = r'(?<!LBA\s)(?<!LBA)(SO\s+\d+)\s+(.+?)(?=\n(?:OP\s+\d+|SO\s+\d+|LBA\s+OP|LBA\s+SO|Index|Late-Breaking|$))'
        so_matches = re.findall(so_pattern, text, re.IGNORECASE | re.DOTALL)
        
        so_sessions = []
        for code, title in so_matches:
            title_clean = title.strip().replace('\n', ' ').replace('\r', ' ')
            # Nettoyer les espaces multiples
            title_clean = re.sub(r'\s+', ' ', title_clean)
            # Arrêter au prochain code de session
            title_clean = re.sub(r'\s+(OP\s+\d+|SO\s+\d+|LBA\s+OP|LBA\s+SO).*$', '', title_clean, flags=re.IGNORECASE)
            if 'WITHDRAWN' in title_clean.upper():
                title_clean = 'WITHDRAWN'
            so_sessions.append({
                "code": code.strip(),
                "title": title_clean
            })
            sessions.append({
                "code": code.strip(),
                "title": title_clean,
                "section": "Abstracts",
                "subsection": "Index of Short Oral Discussions"
            })
        
        if so_sessions:
            abstracts_section["subsections"].append({
                "name": "Index of Short Oral Discussions",
                "level": 2,
                "sessions": so_sessions
            })
        
        sections.append(abstracts_section)
    
    # Late-Breaking Abstracts - Détection améliorée
    lba_section = None
    if 'Late-Breaking Abstracts' in text or 'LBA' in text:
        lba_section = {
            "name": "Late-Breaking Abstracts",
            "level": 1,
            "subsections": []
        }
        
        # Détecter les sessions LBA OP
        lba_op_pattern = r'(LBA\s+OP\s+\d+)\s+(.+?)(?=\n(?:OP\s+\d+|SO\s+\d+|LBA\s+OP\s+\d+|LBA\s+SO\s+\d+|Index|Late-Breaking|$))'
        lba_op_matches = re.findall(lba_op_pattern, text, re.IGNORECASE | re.DOTALL)
        
        lba_op_sessions = []
        for code, title in lba_op_matches:
            title_clean = title.strip().replace('\n', ' ').replace('\r', ' ')
            # Nettoyer les espaces multiples
            title_clean = re.sub(r'\s+', ' ', title_clean)
            # Arrêter au prochain code de session
            title_clean = re.sub(r'\s+(OP\s+\d+|SO\s+\d+|LBA\s+OP|LBA\s+SO).*$', '', title_clean, flags=re.IGNORECASE)
            if 'WITHDRAWN' in title_clean.upper():
                title_clean = 'WITHDRAWN'
            lba_op_sessions.append({
                "code": code.strip(),
                "title": title_clean
            })
            sessions.append({
                "code": code.strip(),
                "title": title_clean,
                "section": "Late-Breaking Abstracts",
                "subsection": "Index of Oral Presentations"
            })
        
        if lba_op_sessions:
            lba_section["subsections"].append({
                "name": "Index of Oral Presentations",
                "level": 2,
                "sessions": lba_op_sessions
            })
        
        # Détecter les sessions LBA SO
        lba_so_pattern = r'(LBA\s+SO\s+\d+)\s+(.+?)(?=\n(?:OP\s+\d+|SO\s+\d+|LBA\s+OP\s+\d+|LBA\s+SO\s+\d+|Index|Late-Breaking|$))'
        lba_so_matches = re.findall(lba_so_pattern, text, re.IGNORECASE | re.DOTALL)
        
        lba_so_sessions = []
        for code, title in lba_so_matches:
            title_clean = title.strip().replace('\n', ' ').replace('\r', ' ')
            # Nettoyer les espaces multiples
            title_clean = re.sub(r'\s+', ' ', title_clean)
            # Arrêter au prochain code de session
            title_clean = re.sub(r'\s+(OP\s+\d+|SO\s+\d+|LBA\s+OP|LBA\s+SO).*$', '', title_clean, flags=re.IGNORECASE)
            if 'WITHDRAWN' in title_clean.upper():
                title_clean = 'WITHDRAWN'
            lba_so_sessions.append({
                "code": code.strip(),
                "title": title_clean
            })
            sessions.append({
                "code": code.strip(),
                "title": title_clean,
                "section": "Late-Breaking Abstracts",
                "subsection": "Index of Short Oral Discussions"
            })
        
        if lba_so_sessions:
            lba_section["subsections"].append({
                "name": "Index of Short Oral Discussions",
                "level": 2,
                "sessions": lba_so_sessions
            })
        
        if lba_section and (lba_op_sessions or lba_so_sessions):
            sections.append(lba_section)
    
    return {
        "sections": sections,
        "sessions": sessions  # Retourner aussi la liste des sessions
    }


def analyze_with_llm(text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyse le texte avec un LLM (OpenAI) pour extraire les métadonnées et la table des matières.
    
    Args:
        text: Texte extrait des pages
        api_key: Clé API OpenAI (optionnel, peut être dans env)
    
    Returns:
        Dictionnaire avec metadata, table_of_contents et sessions
    """
    if not OPENAI_AVAILABLE:
        raise ImportError("OpenAI non disponible. Installez avec: pip install openai")
    
    client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
    
    prompt = f"""Analyse le texte suivant extrait des premières pages d'un document scientifique (supplément de journal avec abstracts).

Extrais et structure les informations suivantes en JSON :

1. MÉTADONNÉES (dans l'en-tête) :
   - tech_document_name : Nom technique complet (ex: "Diabetologia (2025) 68 (Suppl 1):S1–S754")
   - page_interne_debut : Première page (ex: "S1")
   - page_interne_fin : Dernière page (ex: "S754")
   - year : Année (ex: 2025)
   - DOI_num_editeur : Numéro d'éditeur du DOI (ex: "1007")
   - DOI_num_doc : Numéro de document du DOI (ex: "s00125-025-06497-1")
   - lien_doi : Lien DOI complet
   - journal : Nom du journal (ex: "Diabetologia")
   - DOI : Préfixe DOI (ex: "10.1007")
   - nature_contenu : Toujours "ABSTRACTS"
   - doc_title : Titre de l'événement
   - event_city : Ville et pays
   - date_event_start : Date de début (format YYYY-MM-DD)
   - date_event_end : Date de fin (format YYYY-MM-DD)

2. TABLE DES MATIÈRES (hiérarchie) :
   Structure avec sections (niveau 1), subsections (niveau 2), et sessions (niveau 3).
   Format des sessions : CODE TITRE (ex: "OP 01 Influencing cardiovascular outcomes...")
   IMPORTANT : Distingue bien les sessions normales (OP 01, SO 01) des sessions LBA (LBA OP 01, LBA SO 01).
   Les sessions LBA doivent être dans la section "Late-Breaking Abstracts".
   Si une session contient "WITHDRAWN", le titre devient "WITHDRAWN".

3. SESSIONS (liste consolidée) :
   Liste plate de toutes les sessions avec code, title, section, subsection.
   Les codes LBA doivent inclure "LBA" (ex: "LBA OP 01", "LBA SO 01").

4. STATISTIQUES :
   - total_sessions : Nombre total de sessions
   - sessions_by_section : Comptage par section/subsection

Retourne UNIQUEMENT un JSON valide avec cette structure :
{{
  "metadata": {{ ... }},
  "table_of_contents": {{
    "sections": [
      {{
        "name": "...",
        "level": 1,
        "subsections": [
          {{
            "name": "...",
            "level": 2,
            "sessions": [
              {{ "code": "...", "title": "..." }}
            ]
          }}
        ]
      }}
    ]
  }},
  "sessions": [
    {{ "code": "...", "title": "...", "section": "...", "subsection": "..." }}
  ],
  "statistics": {{
    "total_sessions": 0,
    "sessions_by_section": {{ ... }}
  }}
}}

TEXTE À ANALYSER :
{text}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # ou "gpt-3.5-turbo" pour plus rapide/économique
            messages=[
                {"role": "system", "content": "Tu es un expert en extraction de données structurées depuis des documents scientifiques. Tu retournes UNIQUEMENT du JSON valide, sans markdown, sans explications."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    
    except Exception as e:
        print(f"ERREUR lors de l'appel LLM : {e}")
        raise


def calculate_statistics(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcule les statistiques à partir de la liste des sessions.
    
    Args:
        sessions: Liste des sessions
    
    Returns:
        Dictionnaire de statistiques
    """
    stats = {
        "total_sessions": len(sessions),
        "sessions_by_section": {}
    }
    
    for session in sessions:
        section = session.get("section", "Unknown")
        subsection = session.get("subsection", "Unknown")
        
        if section not in stats["sessions_by_section"]:
            stats["sessions_by_section"][section] = {}
        
        if subsection not in stats["sessions_by_section"][section]:
            stats["sessions_by_section"][section][subsection] = 0
        
        stats["sessions_by_section"][section][subsection] += 1
    
    return stats


def process_pdf(
    pdf_path: Path,
    output_path: Path,
    start_page: int = 1,
    end_page: int = 3,
    use_llm: bool = True,
    api_key: Optional[str] = None
) -> None:
    """
    Traite le PDF et génère le fichier intro_json.
    
    Args:
        pdf_path: Chemin vers le PDF
        output_path: Chemin vers le fichier JSON de sortie
        start_page: Page de début
        end_page: Page de fin
        use_llm: Si True, utilise un LLM pour l'analyse
        api_key: Clé API OpenAI (optionnel)
    """
    print(f"Extraction du texte des pages {start_page} à {end_page}...")
    text = extract_text_from_pdf_pages(pdf_path, start_page, end_page)
    text = clean_text(text)
    
    if use_llm and OPENAI_AVAILABLE:
        print("Analyse avec LLM...")
        try:
            result = analyze_with_llm(text, api_key)
        except Exception as e:
            print(f"ERREUR LLM : {e}")
            print("Basculement vers le parsing basique...")
            use_llm = False
    
    if not use_llm:
        print("Analyse avec parsing basique (regex)...")
        metadata = parse_metadata_basic(text)
        table_of_contents_result = parse_table_of_contents_basic(text)
        
        # Extraire les sessions directement depuis le retour de parse_table_of_contents_basic
        sessions = table_of_contents_result.get("sessions", [])
        
        # Reconstruire table_of_contents sans la clé sessions
        table_of_contents = {
            "sections": table_of_contents_result.get("sections", [])
        }
        
        statistics = calculate_statistics(sessions)
        
        result = {
            "metadata": metadata,
            "table_of_contents": table_of_contents,
            "sessions": sessions,
            "statistics": statistics
        }
    
    # Sauvegarder
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] Fichier genere : {output_path}")
    print(f"  Metadonnees : {len(result.get('metadata', {}))} champs")
    print(f"  Sections : {len(result.get('table_of_contents', {}).get('sections', []))}")
    print(f"  Sessions : {result.get('statistics', {}).get('total_sessions', 0)}")


def main() -> None:
    """Point d'entrée principal."""
    # Charger les variables d'environnement depuis .env si disponible
    if DOTENV_AVAILABLE:
        load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Analyse les pages d'introduction d'un PDF et génère intro_json."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Fichier PDF d'entrée.",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Fichier JSON de sortie (intro_json).",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Page de début (défaut: 1).",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        default=3,
        help="Page de fin (défaut: 3).",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Désactive l'utilisation du LLM (parsing basique uniquement).",
    )
    parser.add_argument(
        "--api-key",
        help="Clé API OpenAI (sinon utilise OPENAI_API_KEY de l'environnement).",
    )
    
    args = parser.parse_args()
    pdf_path = Path(args.input)
    output_path = Path(args.output)
    
    process_pdf(
        pdf_path,
        output_path,
        start_page=args.start_page,
        end_page=args.end_page,
        use_llm=not args.no_llm,
        api_key=args.api_key
    )


if __name__ == "__main__":
    main()

