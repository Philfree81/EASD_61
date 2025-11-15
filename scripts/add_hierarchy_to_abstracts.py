#!/usr/bin/env python3
"""
Script pour ajouter la hiérarchie (section → subsection → session) à chaque abstract.

Ce script :
1. Lit le fichier enrichi (neutral_typed_pass3c_enriched.json)
2. Associe chaque abstract à sa session basé sur l'ordre séquentiel
3. Ajoute un champ "hierarchy" à chaque abstract avec :
   - section_name
   - subsection_name
   - session_code
   - session_title
   - hierarchy_level (1=section, 2=subsection, 3=session, 4=abstract)

Usage:
    python scripts/add_hierarchy_to_abstracts.py \
      -i neutral_typed_pass3c_enriched.json \
      -o neutral_typed_pass3c_with_hierarchy.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Charge un fichier JSON."""
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier non trouvé : {file_path}")
    
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_sessions_from_pass2(pass2_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Extrait les sessions depuis pass2 avec leur position et abstract_id.
    
    Args:
        pass2_path: Chemin vers neutral_typed_pass2.json
    
    Returns:
        Dictionnaire {abstract_id: session_info} ou mapping par position
    """
    if not pass2_path.exists():
        return {}
    
    print(f"  Lecture de {pass2_path} pour extraire les sessions...")
    with pass2_path.open("r", encoding="utf-8") as f:
        pass2_data = json.load(f)
    
    elements = pass2_data.get("elements", [])
    
    # Extraire tous les éléments de type "session"
    # ET les éléments qui contiennent des codes de session (pour LBA qui ont une signature différente)
    session_elements = []
    import re
    session_code_pattern_check = re.compile(r'^(LBA\s+)?([A-Z]{2,3})\s+(\d+)')
    
    for e in elements:
        if e.get("element_type") == "session":
            session_elements.append(e)
        else:
            # Vérifier si le texte commence par un code de session (pour LBA)
            text = e.get("text", "").strip()
            if session_code_pattern_check.match(text):
                # C'est probablement une session LBA
                session_elements.append(e)
    
    # Construire un mapping : pour chaque session, trouver les abstracts qui suivent
    # en utilisant la position (page, line_num)
    session_abstract_map = {}
    session_positions = []  # Liste des sessions avec leur position pour mapping par proximité
    
    # Trier les sessions par position
    session_elements.sort(key=lambda e: (
        e.get("page", 0),
        e.get("line_num", 0),
        e.get("position", {}).get("x", 0.0)
    ))
    
    # Extraire le code de session depuis le texte
    # Supporte : "OP 01", "SO 068", "LBA OP 01", "LBA SO 01"
    import re
    session_code_pattern = re.compile(r'^(LBA\s+)?([A-Z]{2,3})\s+(\d+)\s+')
    
    # Grouper les éléments de session par session_code
    # Une session peut être sur plusieurs lignes (ex: "OP 01" puis "Influencing...")
    sessions_by_code = {}  # {session_code: {text_parts: [], page, line, abstract_id}}
    
    for session_elem in session_elements:
        text = session_elem.get("text", "").strip()
        page = session_elem.get("page", 0)
        line = session_elem.get("line_num", 0)
        abstract_id = session_elem.get("abstract_id")
        
        # Vérifier si c'est le début d'une nouvelle session (contient un code)
        match = session_code_pattern.match(text)
        if match:
            lba_prefix = match.group(1)  # "LBA " ou None
            session_type = match.group(2)  # "OP" ou "SO"
            session_num = match.group(3)  # "01", "068", etc.
            
            # Construire le code complet : "OP 01" ou "LBA OP 01"
            if lba_prefix:
                session_code = f"LBA {session_type} {session_num}"
            else:
                session_code = f"{session_type} {session_num}"
            # Nouvelle session ou session existante
            if session_code not in sessions_by_code:
                sessions_by_code[session_code] = {
                    "code": session_code,
                    "text_parts": [text],
                    "page": page,
                    "line": line,
                    "abstract_id": abstract_id
                }
            else:
                # Session déjà vue, ajouter le texte
                sessions_by_code[session_code]["text_parts"].append(text)
                # Mettre à jour la position si plus tôt
                if page < sessions_by_code[session_code]["page"] or (
                    page == sessions_by_code[session_code]["page"] and 
                    line < sessions_by_code[session_code]["line"]
                ):
                    sessions_by_code[session_code]["page"] = page
                    sessions_by_code[session_code]["line"] = line
                # Prendre le premier abstract_id trouvé
                if abstract_id and not sessions_by_code[session_code]["abstract_id"]:
                    sessions_by_code[session_code]["abstract_id"] = abstract_id
        else:
            # Texte de continuation - trouver la session la plus proche précédente
            # Chercher la dernière session sur la même page ou page précédente
            closest_session_code = None
            closest_distance = float('inf')
            
            for code, session_data in sessions_by_code.items():
                session_page = session_data["page"]
                session_line = session_data["line"]
                
                # Session doit être avant ou sur la même page
                if session_page < page or (session_page == page and session_line < line):
                    distance = (page - session_page) * 1000 + (line - session_line)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_session_code = code
            
            if closest_session_code:
                sessions_by_code[closest_session_code]["text_parts"].append(text)
                if abstract_id and not sessions_by_code[closest_session_code]["abstract_id"]:
                    sessions_by_code[closest_session_code]["abstract_id"] = abstract_id
    
    # Construire la liste finale des sessions
    for session_code, session_data in sessions_by_code.items():
        # Concaténer les parties du texte
        full_text = " ".join(session_data["text_parts"])
        # Nettoyer : enlever les codes de session supplémentaires qui pourraient être dans le texte
        # (ex: "OP 01 Title LBA OP 02" -> "OP 01 Title")
        cleaned_text = full_text
        # Trouver le premier code de session et prendre tout jusqu'au prochain code ou fin
        first_match = session_code_pattern.search(cleaned_text)
        if first_match:
            start_pos = first_match.start()
            # Chercher le prochain code de session après le premier
            remaining = cleaned_text[start_pos + len(session_code):]
            next_match = session_code_pattern.search(remaining)
            if next_match:
                # Couper au prochain code
                cleaned_text = cleaned_text[:start_pos + len(session_code) + next_match.start()].strip()
            else:
                cleaned_text = cleaned_text[start_pos:].strip()
        
        session_positions.append({
            "code": session_code,
            "text": cleaned_text,
            "page": session_data["page"],
            "line": session_data["line"],
            "abstract_id": session_data["abstract_id"]
        })
    
    # Créer le mapping : sessions avec abstract_id direct
    for session_pos in session_positions:
        if session_pos["abstract_id"]:
            session_abstract_map[session_pos["abstract_id"]] = {
                "session_code": session_pos["code"],
                "session_text": session_pos["text"],
                "page": session_pos["page"],
                "line": session_pos["line"]
            }
    
    print(f"  {len(session_positions)} sessions trouvees dans pass2")
    print(f"  {len(session_abstract_map)} sessions avec abstract_id direct")
    
    # Retourner aussi les positions pour mapping par proximité
    return {
        "direct_mapping": session_abstract_map,
        "positions": session_positions
    }


def build_session_abstract_mapping(
    sessions: List[Dict[str, Any]],
    abstracts: List[Dict[str, Any]],
    section_toc: Optional[Dict[str, Any]] = None,
    pass2_path: Optional[Path] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Construit un mapping entre les abstracts et les sessions.
    
    La hiérarchie vient de :
    - section_TOC : Table des matières avec structure hiérarchique (section → subsection → session)
    - sessions : Liste plate des sessions avec section/subsection
    
    Stratégie de mapping :
    1. Utiliser l'ordre séquentiel des abstracts et des sessions
    2. Les abstracts sont distribués aux sessions dans l'ordre d'apparition
    3. Une session peut contenir plusieurs abstracts (distribution séquentielle)
    
    Args:
        sessions: Liste des sessions depuis le fichier enrichi
        abstracts: Liste des abstracts
        section_toc: Table des matières (optionnel, pour validation)
    
    Returns:
        Dictionnaire {abstract_id: session_info}
    """
    # Essayer d'utiliser pass2 pour un mapping précis
    pass2_data = {}
    if pass2_path:
        pass2_data = extract_sessions_from_pass2(pass2_path)
    
    pass2_session_map = pass2_data.get("direct_mapping", {})
    session_positions = pass2_data.get("positions", [])
    
    # Créer un dictionnaire de sessions indexé par code pour lookup rapide
    # Préférer les titres depuis section_TOC (table_of_contents) qui sont plus propres
    sessions_by_code = {}
    
    # D'abord, extraire depuis section_TOC si disponible (titres plus propres)
    if section_toc:
        for section in section_toc.get("sections", []):
            section_name = section.get("name", "")
            for subsection in section.get("subsections", []):
                subsection_name = subsection.get("name", "")
                for session in subsection.get("sessions", []):
                    code = session.get("code", "").strip()
                    if code and code not in sessions_by_code:
                        sessions_by_code[code] = {
                            "code": code,
                            "title": session.get("title", ""),
                            "section": section_name,
                            "subsection": subsection_name
                        }
    
    # Ensuite, compléter avec sessions (pour section/subsection si manquant)
    for session in sessions:
        code = session.get("code", "").strip()
        if code:
            if code not in sessions_by_code:
                # Nouvelle session non trouvée dans section_TOC
                sessions_by_code[code] = {
                    "code": code,
                    "title": session.get("title", ""),
                    "section": session.get("section", ""),
                    "subsection": session.get("subsection", "")
                }
            else:
                # Session existe déjà, mettre à jour section/subsection si manquant
                if not sessions_by_code[code]["section"]:
                    sessions_by_code[code]["section"] = session.get("section", "")
                if not sessions_by_code[code]["subsection"]:
                    sessions_by_code[code]["subsection"] = session.get("subsection", "")
    
    # Créer une liste plate de toutes les sessions dans l'ordre (fallback)
    ordered_sessions = []
    for session in sessions:
        ordered_sessions.append({
            "code": session.get("code", ""),
            "title": session.get("title", ""),
            "section": session.get("section", ""),
            "subsection": session.get("subsection", "")
        })
    
    # Filtrer les abstracts valides (non WITHDRAWN) et les trier par page/ordre
    valid_abstracts = [
        abs for abs in abstracts
        if abs.get("title", "").strip().upper() != "WITHDRAWN"
    ]
    
    # Trier les abstracts par page_start puis abstract_code pour garantir l'ordre
    def safe_int_code(code):
        """Convertit un code en int de manière sûre."""
        if not code:
            return 0
        code_str = str(code).strip()
        # Extraire les chiffres du début
        import re
        match = re.match(r'^(\d+)', code_str)
        if match:
            return int(match.group(1))
        return 0
    
    valid_abstracts.sort(key=lambda a: (
        a.get("page_start", 0),
        safe_int_code(a.get("abstract_code", ""))
    ))
    
    # Mapping : utiliser pass2 si disponible, sinon fallback séquentiel
    mapping = {}
    session_idx = 0
    current_session_code = None
    
    for abstract in abstracts:
        abstract_id = abstract.get("abstract_id", "")
        abstract_code = abstract.get("abstract_code", "")
        
        # Si WITHDRAWN, pas de session associée
        if abstract.get("title", "").strip().upper() == "WITHDRAWN":
            mapping[abstract_id] = {
                "section": None,
                "subsection": None,
                "session_code": None,
                "session_title": "WITHDRAWN"
            }
            continue
        
        # Stratégie 1 : Utiliser pass2 si disponible
        if pass2_session_map and abstract_id in pass2_session_map:
            session_info_pass2 = pass2_session_map[abstract_id]
            session_code = session_info_pass2.get("session_code", "")
            
            if session_code in sessions_by_code:
                # Utiliser le titre depuis metadata.json (sessions) plutôt que depuis pass2
                session = sessions_by_code[session_code]
                mapping[abstract_id] = {
                    "section": session["section"],
                    "subsection": session["subsection"],
                    "session_code": session["code"],
                    "session_title": session["title"]  # Titre depuis metadata.json
                }
                current_session_code = session_code
                continue
        
        # Stratégie 2 : Utiliser la position pour trouver la session la plus proche
        # (si pass2 disponible mais pas de mapping direct)
        if session_positions and not pass2_session_map.get(abstract_id):
            abstract_page = abstract.get("page_start", 0)
            
            # Trouver la session la plus proche (dernière session avant cet abstract)
            closest_session = None
            for session_pos in session_positions:
                session_page = session_pos.get("page", 0)
                session_line = session_pos.get("line", 0)
                
                # Session doit être avant ou sur la même page que l'abstract
                if session_page < abstract_page or (session_page == abstract_page):
                    if not closest_session or (
                        session_page > closest_session.get("page", 0) or
                        (session_page == closest_session.get("page", 0) and 
                         session_line > closest_session.get("line", 0))
                    ):
                        closest_session = session_pos
            
            if closest_session:
                session_code = closest_session.get("code", "")
                if session_code in sessions_by_code:
                    session = sessions_by_code[session_code]
                    mapping[abstract_id] = {
                        "section": session["section"],
                        "subsection": session["subsection"],
                        "session_code": session["code"],
                        "session_title": session["title"]
                    }
                    current_session_code = session_code
                    continue
        
        # Stratégie 3 : Utiliser la session courante (plusieurs abstracts par session)
        # Si on a déjà une session courante, on continue avec elle
        if current_session_code and current_session_code in sessions_by_code:
            session = sessions_by_code[current_session_code]
            mapping[abstract_id] = {
                "section": session["section"],
                "subsection": session["subsection"],
                "session_code": session["code"],
                "session_title": session["title"]
            }
            continue
        
        # Stratégie 4 : Fallback séquentiel (nouvelle session)
        if session_idx < len(ordered_sessions):
            session = ordered_sessions[session_idx]
            mapping[abstract_id] = {
                "section": session["section"],
                "subsection": session["subsection"],
                "session_code": session["code"],
                "session_title": session["title"]
            }
            current_session_code = session["code"]
            session_idx += 1
        else:
            # Plus de sessions disponibles
            mapping[abstract_id] = {
                "section": None,
                "subsection": None,
                "session_code": None,
                "session_title": None
            }
    
    return mapping


def add_hierarchy_to_abstract(
    abstract: Dict[str, Any],
    session_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Ajoute la hiérarchie à un abstract.
    
    Args:
        abstract: Abstract à enrichir
        session_info: Informations de session
    
    Returns:
        Abstract enrichi avec hierarchy
    """
    enriched = abstract.copy()
    
    # Construire la hiérarchie
    hierarchy = {
        "level_1_section": {
            "name": session_info.get("section"),
            "level": 1
        },
        "level_2_subsection": {
            "name": session_info.get("subsection"),
            "level": 2
        },
        "level_3_session": {
            "code": session_info.get("session_code"),
            "title": session_info.get("session_title"),
            "level": 3
        },
        "level_4_abstract": {
            "abstract_id": abstract.get("abstract_id"),
            "abstract_code": abstract.get("abstract_code"),
            "level": 4
        }
    }
    
    enriched["hierarchy"] = hierarchy
    
    return enriched


def process_file(
    input_path: Path,
    output_path: Path,
    pass2_path: Optional[Path] = None
) -> None:
    """
    Traite le fichier et ajoute la hiérarchie aux abstracts.
    
    Args:
        input_path: Fichier enrichi d'entrée
        output_path: Fichier de sortie avec hiérarchie
    """
    print(f"Chargement de {input_path}...")
    data = load_json_file(input_path)
    
    # Vérifier la structure
    if "abstracts" not in data:
        raise ValueError("Le fichier doit contenir une clé 'abstracts'")
    
    if "sessions" not in data:
        raise ValueError("Le fichier doit contenir une clé 'sessions'")
    
    abstracts = data["abstracts"]
    sessions = data["sessions"]
    
    print(f"  {len(abstracts)} abstracts trouvés")
    print(f"  {len(sessions)} sessions trouvées")
    
    # Récupérer section_TOC pour référence (optionnel)
    section_toc = data.get("section_TOC")
    
    # Construire le mapping abstract -> session
    print("Construction du mapping abstract -> session...")
    print("  La hiérarchie vient de section_TOC et sessions (depuis metadata.json)")
    if pass2_path:
        print(f"  Utilisation de {pass2_path} pour un mapping precis")
    mapping = build_session_abstract_mapping(sessions, abstracts, section_toc, pass2_path)
    
    # Enrichir chaque abstract avec la hiérarchie
    print("Ajout de la hiérarchie aux abstracts...")
    enriched_abstracts = []
    matched_count = 0
    unmatched_count = 0
    
    for abstract in abstracts:
        abstract_id = abstract.get("abstract_id", "")
        session_info = mapping.get(abstract_id, {})
        
        if session_info.get("session_code"):
            matched_count += 1
        else:
            unmatched_count += 1
        
        enriched = add_hierarchy_to_abstract(abstract, session_info)
        enriched_abstracts.append(enriched)
    
    # Créer une structure hiérarchique imbriquée : sections → subsections → sessions → abstracts
    print("Création de la structure hiérarchique imbriquée...")
    
    # Grouper les abstracts par session
    abstracts_by_session = {}  # {session_code: [abstracts]}
    abstracts_without_session = []
    
    for abstract in enriched_abstracts:
        hierarchy = abstract.get("hierarchy", {})
        session = hierarchy.get("level_3_session", {})
        session_code = session.get("code")
        
        if session_code:
            if session_code not in abstracts_by_session:
                abstracts_by_session[session_code] = []
            abstracts_by_session[session_code].append(abstract)
        else:
            abstracts_without_session.append(abstract)
    
    # Construire la structure hiérarchique depuis section_TOC
    hierarchical_sections = []
    
    if section_toc:
        for section in section_toc.get("sections", []):
            section_name = section.get("name", "")
            hierarchical_section = {
                "name": section_name,
                "level": section.get("level", 1),
                "subsections": []
            }
            
            for subsection in section.get("subsections", []):
                subsection_name = subsection.get("name", "")
                hierarchical_subsection = {
                    "name": subsection_name,
                    "level": subsection.get("level", 2),
                    "sessions": []
                }
                
                for session_ref in subsection.get("sessions", []):
                    session_code = session_ref.get("code", "").strip()
                    session_title = session_ref.get("title", "")
                    
                    # Récupérer les abstracts de cette session
                    session_abstracts = abstracts_by_session.get(session_code, [])
                    
                    hierarchical_session = {
                        "code": session_code,
                        "title": session_title,
                        "abstracts": session_abstracts
                    }
                    
                    hierarchical_subsection["sessions"].append(hierarchical_session)
                
                hierarchical_section["subsections"].append(hierarchical_subsection)
            
            hierarchical_sections.append(hierarchical_section)
    
    # Structure de sortie
    output_data = {}
    
    # 1. Metadata en premier
    if "metadata" in data:
        output_data["metadata"] = data["metadata"]
    
    # 2. Sections hiérarchiques avec abstracts imbriqués
    output_data["sections"] = hierarchical_sections
    
    # 3. Abstracts sans session (si présents)
    if abstracts_without_session:
        output_data["abstracts_without_session"] = abstracts_without_session
    
    # Conserver section_TOC et sessions pour référence (optionnel)
    if "section_TOC" in data:
        output_data["section_TOC"] = data["section_TOC"]
    if "sessions" in data:
        output_data["sessions"] = data["sessions"]
    
    # Sauvegarder
    print(f"Sauvegarde dans {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Fichier avec hiérarchie genere : {output_path}")
    print(f"  Abstracts avec session : {matched_count}")
    print(f"  Abstracts sans session : {unmatched_count}")
    
    # Afficher quelques exemples
    print(f"\nExemples de hiérarchie :")
    for i, abstract in enumerate(enriched_abstracts[:3]):
        hierarchy = abstract.get("hierarchy", {})
        session = hierarchy.get("level_3_session", {})
        print(f"  Abstract {abstract.get('abstract_code')}: {session.get('code')} - {session.get('title', '')[:50]}...")


def main() -> None:
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Ajoute la hiérarchie (section/subsection/session) aux abstracts."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Fichier enrichi d'entrée (neutral_typed_pass3c_enriched.json).",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Fichier de sortie avec hiérarchie.",
    )
    parser.add_argument(
        "--pass2",
        help="Fichier pass2 (neutral_typed_pass2.json) pour mapping precis des sessions.",
    )
    
    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    pass2_path = Path(args.pass2) if args.pass2 else None
    
    process_file(input_path, output_path, pass2_path)


if __name__ == "__main__":
    main()

