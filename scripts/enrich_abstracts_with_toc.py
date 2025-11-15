#!/usr/bin/env python3
"""
Script pour enrichir neutral_typed_pass3c.json avec les sections et sessions
depuis metadata.json (table des matières).

Ce script :
1. Lit metadata.json (contient table_of_contents et sessions)
2. Lit neutral_typed_pass3c.json (contient les abstracts)
3. Ajoute section_TOC et sessions au fichier pass3c
4. Sauvegarde le fichier enrichi

Usage:
    python scripts/enrich_abstracts_with_toc.py \
      -m metadata.json \
      -a neutral_typed_pass3c.json \
      -o neutral_typed_pass3c_enriched.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """
    Charge un fichier JSON.
    
    Args:
        file_path: Chemin vers le fichier JSON
    
    Returns:
        Données JSON chargées
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier non trouvé : {file_path}")
    
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_table_of_contents(metadata_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait la table des matières depuis metadata.json.
    
    Args:
        metadata_data: Données du fichier metadata.json
    
    Returns:
        Table des matières structurée
    """
    if "table_of_contents" not in metadata_data:
        raise ValueError("metadata.json doit contenir une clé 'table_of_contents'")
    
    return metadata_data["table_of_contents"]


def extract_sessions(metadata_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrait la liste des sessions depuis metadata.json.
    
    Args:
        metadata_data: Données du fichier metadata.json
    
    Returns:
        Liste des sessions
    """
    if "sessions" not in metadata_data:
        # Si pas de clé sessions, construire depuis table_of_contents
        sessions = []
        toc = metadata_data.get("table_of_contents", {})
        
        for section in toc.get("sections", []):
            section_name = section.get("name", "")
            for subsection in section.get("subsections", []):
                subsection_name = subsection.get("name", "")
                for session in subsection.get("sessions", []):
                    sessions.append({
                        "code": session.get("code", ""),
                        "title": session.get("title", ""),
                        "section": section_name,
                        "subsection": subsection_name
                    })
        
        return sessions
    
    return metadata_data["sessions"]


def extract_metadata(metadata_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les métadonnées du document depuis metadata.json.
    
    Args:
        metadata_data: Données du fichier metadata.json
    
    Returns:
        Métadonnées du document
    """
    if "metadata" not in metadata_data:
        raise ValueError("metadata.json doit contenir une clé 'metadata'")
    
    return metadata_data["metadata"]


def enrich_abstracts_file(
    abstracts_data: Dict[str, Any],
    metadata: Dict[str, Any],
    table_of_contents: Dict[str, Any],
    sessions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Enrichit le fichier abstracts avec metadata, section_TOC et sessions.
    
    Args:
        abstracts_data: Données du fichier neutral_typed_pass3c.json
        metadata: Métadonnées du document à ajouter en tête
        table_of_contents: Table des matières à ajouter
        sessions: Liste des sessions à ajouter
    
    Returns:
        Données enrichies
    """
    # Créer un nouveau dictionnaire avec l'ordre souhaité
    enriched_data = {}
    
    # 1. Métadonnées en premier (en-tête du document)
    enriched_data["metadata"] = metadata
    
    # 2. Abstracts existants
    enriched_data["abstracts"] = abstracts_data.get("abstracts", [])
    
    # 3. Table des matières
    enriched_data["section_TOC"] = table_of_contents
    
    # 4. Sessions
    enriched_data["sessions"] = sessions
    
    # Préserver d'autres clés éventuelles de abstracts_data
    for key, value in abstracts_data.items():
        if key not in ["abstracts"]:  # abstracts déjà ajouté
            enriched_data[key] = value
    
    return enriched_data


def process_files(
    metadata_path: Path,
    abstracts_path: Path,
    output_path: Path
) -> None:
    """
    Traite les fichiers et génère le fichier enrichi.
    
    Args:
        metadata_path: Chemin vers metadata.json
        abstracts_path: Chemin vers neutral_typed_pass3c.json
        output_path: Chemin vers le fichier de sortie enrichi
    """
    print(f"Chargement de {metadata_path}...")
    metadata_data = load_json_file(metadata_path)
    
    print(f"Chargement de {abstracts_path}...")
    abstracts_data = load_json_file(abstracts_path)
    
    # Extraire les métadonnées du document
    print("Extraction des métadonnées du document...")
    metadata = extract_metadata(metadata_data)
    
    # Extraire les données de la table des matières
    print("Extraction de la table des matières...")
    table_of_contents = extract_table_of_contents(metadata_data)
    
    print("Extraction des sessions...")
    sessions = extract_sessions(metadata_data)
    
    # Enrichir le fichier abstracts
    print("Enrichissement du fichier abstracts...")
    enriched_data = enrich_abstracts_file(
        abstracts_data,
        metadata,
        table_of_contents,
        sessions
    )
    
    # Sauvegarder
    print(f"Sauvegarde dans {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(enriched_data, f, ensure_ascii=False, indent=2)
    
    # Statistiques
    num_abstracts = len(enriched_data.get("abstracts", []))
    num_sections = len(table_of_contents.get("sections", []))
    num_sessions = len(sessions)
    num_metadata_fields = len(metadata)
    
    print(f"\n[OK] Fichier enrichi genere : {output_path}")
    print(f"  Metadonnees : {num_metadata_fields} champs")
    print(f"  Abstracts : {num_abstracts}")
    print(f"  Sections TOC : {num_sections}")
    print(f"  Sessions : {num_sessions}")
    
    # Afficher la structure des sections
    print(f"\nStructure des sections :")
    for section in table_of_contents.get("sections", []):
        section_name = section.get("name", "")
        num_subsections = len(section.get("subsections", []))
        total_sessions = sum(
            len(sub.get("sessions", []))
            for sub in section.get("subsections", [])
        )
        print(f"  - {section_name}: {num_subsections} sous-sections, {total_sessions} sessions")


def main() -> None:
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Enrichit neutral_typed_pass3c.json avec les sections et sessions depuis metadata.json."
    )
    parser.add_argument(
        "-m", "--metadata",
        required=True,
        help="Fichier metadata.json (contient table_of_contents et sessions).",
    )
    parser.add_argument(
        "-a", "--abstracts",
        required=True,
        help="Fichier neutral_typed_pass3c.json (contient les abstracts).",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Fichier JSON de sortie enrichi.",
    )
    
    args = parser.parse_args()
    metadata_path = Path(args.metadata)
    abstracts_path = Path(args.abstracts)
    output_path = Path(args.output)
    
    process_files(metadata_path, abstracts_path, output_path)


if __name__ == "__main__":
    main()

