#!/usr/bin/env python3
"""
clean_headers_footers.py

Script intermédiaire pour nettoyer le JSON avant la passe 2 :

- supprime tous les éléments dont element_type est "header" ou "footer"

Usage :
    python clean_headers_footers.py -i neutral_typed_pass1.json -o neutral_typed_pass1_nohf.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Le JSON racine doit être un objet (dict).")
    return data


def save_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean_elements(elements: List[Any]) -> List[Any]:
    """
    Supprime tous les éléments dont element_type est "header" ou "footer".
    On laisse tout le reste inchangé.
    """
    cleaned: List[Any] = []
    removed = 0

    for e in elements:
        if not isinstance(e, dict):
            cleaned.append(e)
            continue

        etype = e.get("element_type")
        if etype in ("header", "footer"):
            removed += 1
            continue

        cleaned.append(e)

    print(f"[clean_headers_footers] Éléments conservés : {len(cleaned)} (supprimés : {removed})")
    return cleaned


def process_file(input_path: Path, output_path: Path) -> None:
    data = load_json(input_path)

    elements = data.get("elements")
    if elements is None:
        raise ValueError("Le JSON d'entrée ne contient pas le champ 'elements'.")
    if not isinstance(elements, list):
        raise ValueError("Le champ 'elements' doit être une liste.")

    cleaned_elements = clean_elements(elements)
    data["elements"] = cleaned_elements

    save_json(output_path, data)
    print(f"[clean_headers_footers] Fichier nettoyé écrit dans : {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Supprime les headers/footers du JSON avant la passe 2."
    )
    parser.add_argument("-i", "--input", required=True, help="Fichier JSON d'entrée (pass1).")
    parser.add_argument("-o", "--output", required=True, help="Fichier JSON de sortie (nettoyé).")
    args = parser.parse_args()

    process_file(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
