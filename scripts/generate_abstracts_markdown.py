#!/usr/bin/env python3
"""
Script pour générer un fichier Markdown formaté à partir d'un fichier JSON pass3.

Le script lit un fichier JSON contenant des abstracts structurés (format pass3)
et génère un fichier Markdown avec un formatage similaire aux abstracts
scientifiques originaux.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


# Mapping des noms de sections vers leurs titres formatés
SECTION_TITLES = {
    "background_and_aims": "Background and aims",
    "materials_and_methods": "Materials and methods",
    "results": "Results",
    "conclusion": "Conclusion",
    "disclosure_text": "Disclosure",
}


def format_authors(authors: List[Dict[str, Any]]) -> str:
    """
    Formate la liste des auteurs en une chaîne Markdown.
    
    Args:
        authors: Liste de dictionnaires avec 'name' et 'indices'
    
    Returns:
        Chaîne formatée avec les auteurs séparés par des virgules
    """
    if not authors:
        return ""
    
    author_names = []
    for author in authors:
        name = author.get("name", "").strip()
        if name:
            author_names.append(name)
    
    return ", ".join(author_names)


def format_institutions(institutions: List[Dict[str, Any]]) -> str:
    """
    Formate la liste des institutions avec leurs indices.
    
    Args:
        institutions: Liste de dictionnaires avec 'index' et 'text'
    
    Returns:
        Chaîne formatée avec les institutions et leurs indices
    """
    if not institutions:
        return ""
    
    # Trier par index
    sorted_inst = sorted(institutions, key=lambda x: x.get("index", 0))
    
    lines = []
    for inst in sorted_inst:
        idx = inst.get("index", 0)
        text = inst.get("text", "").strip()
        if text:
            lines.append(f"{idx}. {text}")
    
    return "\n".join(lines)


def format_abstract(abstract: Dict[str, Any]) -> str:
    """
    Formate un abstract complet en Markdown.
    
    Args:
        abstract: Dictionnaire contenant les données d'un abstract
    
    Returns:
        Chaîne Markdown formatée
    """
    lines = []
    
    # Numéro de l'abstract
    abstract_code = abstract.get("abstract_code", "")
    if abstract_code:
        lines.append(f"**{abstract_code}**")
        lines.append("")
    
    # Titre
    title = abstract.get("title", "").strip()
    if title:
        lines.append(f"**{title}**")
        lines.append("")
    
    # Auteurs
    authors = format_authors(abstract.get("authors", []))
    if authors:
        lines.append(authors)
        lines.append("")
    
    # Institutions
    institutions = format_institutions(abstract.get("institutions", []))
    if institutions:
        lines.append(institutions)
        lines.append("")
    
    # Sections
    sections = abstract.get("sections", {})
    
    # Background and aims
    if "background_and_aims" in sections and sections["background_and_aims"]:
        lines.append(f"**{SECTION_TITLES['background_and_aims']}:**")
        lines.append(sections["background_and_aims"].strip())
        lines.append("")
    
    # Materials and methods
    if "materials_and_methods" in sections and sections["materials_and_methods"]:
        lines.append(f"**{SECTION_TITLES['materials_and_methods']}:**")
        lines.append(sections["materials_and_methods"].strip())
        lines.append("")
    
    # Results
    if "results" in sections and sections["results"]:
        lines.append(f"**{SECTION_TITLES['results']}:**")
        lines.append(sections["results"].strip())
        lines.append("")
    
    # Conclusion
    if "conclusion" in sections and sections["conclusion"]:
        lines.append(f"**{SECTION_TITLES['conclusion']}:**")
        lines.append(sections["conclusion"].strip())
        lines.append("")
    
    # Disclosure
    if "disclosure_text" in sections and sections["disclosure_text"]:
        lines.append(f"**{SECTION_TITLES['disclosure_text']}:**")
        lines.append(sections["disclosure_text"].strip())
        lines.append("")
    
    return "\n".join(lines)


def process_file(
    input_path: Path,
    output_path: Path,
    include_withdrawn: bool = False,
    abstracts_per_file: int = 150
) -> None:
    """
    Traite le fichier JSON et génère plusieurs fichiers Markdown.
    
    Args:
        input_path: Chemin vers le fichier JSON d'entrée
        output_path: Chemin vers le fichier Markdown de sortie (sera utilisé comme base)
        include_withdrawn: Si True, inclut les abstracts WITHDRAWN
        abstracts_per_file: Nombre d'abstracts par fichier (défaut: 150)
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier JSON introuvable : {input_path}")
    
    # Charger le JSON
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not isinstance(data, dict) or "abstracts" not in data:
        raise ValueError("Le JSON doit contenir une clé 'abstracts' avec une liste d'abstracts.")
    
    abstracts = data["abstracts"]
    if not isinstance(abstracts, list):
        raise ValueError("La clé 'abstracts' doit être une liste.")
    
    # Filtrer les abstracts (exclure WITHDRAWN si nécessaire)
    filtered_abstracts = []
    for abstract in abstracts:
        if not isinstance(abstract, dict):
            continue
        
        if not include_withdrawn:
            title = abstract.get("title", "").strip()
            if title.upper() == "WITHDRAWN":
                continue
        
        filtered_abstracts.append(abstract)
    
    # Préparer le nom de base du fichier de sortie
    output_dir = output_path.parent
    output_stem = output_path.stem
    output_suffix = output_path.suffix
    
    # Diviser en lots
    total_abstracts = len(filtered_abstracts)
    num_files = (total_abstracts + abstracts_per_file - 1) // abstracts_per_file  # Arrondi supérieur
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    files_created = []
    
    for file_idx in range(num_files):
        start_idx = file_idx * abstracts_per_file
        end_idx = min(start_idx + abstracts_per_file, total_abstracts)
        batch_abstracts = filtered_abstracts[start_idx:end_idx]
        
        # Générer le nom du fichier
        if num_files == 1:
            # Un seul fichier : utiliser le nom original
            batch_output_path = output_path
        else:
            # Plusieurs fichiers : ajouter un numéro
            batch_output_path = output_dir / f"{output_stem}_part{file_idx + 1:03d}{output_suffix}"
        
        # Générer le Markdown pour ce lot
        markdown_lines = []
        
        # En-tête
        markdown_lines.append("# Abstracts")
        markdown_lines.append("")
        markdown_lines.append(f"*Généré à partir de {input_path.name}*")
        if num_files > 1:
            markdown_lines.append(f"*Partie {file_idx + 1} sur {num_files} (abstracts {start_idx + 1} à {end_idx})*")
        markdown_lines.append("")
        markdown_lines.append("---")
        markdown_lines.append("")
        
        # Traiter chaque abstract du lot
        for abstract in batch_abstracts:
            formatted = format_abstract(abstract)
            if formatted.strip():
                markdown_lines.append(formatted)
                markdown_lines.append("---")
                markdown_lines.append("")
        
        # Écrire le fichier
        with batch_output_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(markdown_lines))
        
        files_created.append(batch_output_path)
        print(f"[OK] Fichier cree : {batch_output_path}")
        print(f"  {len(batch_abstracts)} abstracts (total: {start_idx + 1}-{end_idx})")
    
    print(f"\n[OK] Total : {num_files} fichier(s) cree(s), {total_abstracts} abstracts traites")


def main() -> None:
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Génère un fichier Markdown formaté à partir d'un JSON pass3."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Fichier JSON d'entrée (format pass3).",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Fichier Markdown de sortie.",
    )
    parser.add_argument(
        "--include-withdrawn",
        action="store_true",
        help="Inclure les abstracts WITHDRAWN dans la sortie.",
    )
    parser.add_argument(
        "--per-file",
        type=int,
        default=150,
        help="Nombre d'abstracts par fichier (defaut: 150).",
    )
    
    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    process_file(
        input_path,
        output_path,
        include_withdrawn=args.include_withdrawn,
        abstracts_per_file=args.per_file
    )


if __name__ == "__main__":
    main()

