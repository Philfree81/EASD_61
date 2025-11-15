#!/usr/bin/env python3
# semantic_typing_pass_3.py
"""
Passe 3 : agrégation par abstract à partir des éléments typés en pass2.

Entrée :
    - JSON (dict avec clé "elements") produit par semantic_typing_pass_2.py,
      contenant notamment :
        * abstract_id
        * code_abstract
        * abstract_title
        * author_title
        * author
        * institution
        * indice
        * section_* (labels)
        * section_*_text
        * abstract_text
        * section_disclosure (label)
        * section_disclosure_text (texte disclosure)

Sortie :
    - JSON avec une clé "abstracts" qui contient une liste d'objets abstraits :
        {
          "abstract_id": "abs_0005",
          "abstract_code": "0005",
          "page_start": 5,
          "page_end": 5,
          "title": "...",
          "authors": [
            { "name": "...", "indices": [1, 2] },
            ...
          ],
          "institutions": [
            { "index": 1, "text": "University of Pisa, Pisa, Italy" },
            ...
          ],
          "sections": {
            "background_and_aims": "...",
            "materials_and_methods": "...",
            "results": "...",
            "conclusion": "...",
            "disclosure_text": "..."
          }
        }
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Utilitaires d'ordre / tri
# ---------------------------------------------------------------------------

def element_order_key(e: Dict[str, Any]) -> Tuple[int, int, float, int]:
    """
    Clé de tri globale pour les éléments :
        - page
        - line_num
        - position.x
        - id
    """
    page = e.get("page", 0)
    line_num = e.get("line_num", 0)
    x = e.get("position", {}).get("x", 0.0)
    eid = e.get("id", 0)
    return (page, line_num, x, eid)


def group_by_line(elements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Regroupe par line_id.
    """
    by_line: Dict[str, List[Dict[str, Any]]] = {}
    for e in elements:
        lid = e.get("line_id")
        if lid is None:
            continue
        by_line.setdefault(lid, []).append(e)
    return by_line


def concat_text(elems: List[Dict[str, Any]]) -> str:
    """
    Concatène le texte de plusieurs éléments dans l'ordre PDF.
    """
    ordered = sorted(elems, key=element_order_key)
    parts: List[str] = []
    for e in ordered:
        if e.get("type") == "text":
            txt = e.get("text", "")
            if txt:
                parts.append(txt)
    return " ".join(parts).strip()


# ---------------------------------------------------------------------------
# Parsing auteurs / institutions
# ---------------------------------------------------------------------------

_author_split_re = re.compile(r"\s*,\s*")

# ex : "M. Chiriacò1" -> name="M. Chiriacò", indices=[1]
_author_idx_re = re.compile(r"^(.*?)(\d+(?:,\d+)*)\s*$")


def parse_authors_from_lines(line_texts: List[str]) -> List[Dict[str, Any]]:
    """
    À partir d'une liste de lignes auteur (texte brut), produit une liste
    d'auteurs structurés : {name, indices}.
    On split sur les virgules puis on extrait les indices en suffixe.
    """
    authors: List[Dict[str, Any]] = []
    seen = set()

    for line in line_texts:
        line = line.strip()
        if not line:
            continue

        tokens = _author_split_re.split(line)
        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue

            m = _author_idx_re.match(tok)
            if m:
                name = m.group(1).strip(" ,;")
                idx_part = m.group(2)
                indices = [int(x) for x in idx_part.split(",") if x.isdigit()]
            else:
                name = tok.strip(" ,;")
                indices = []

            if not name:
                continue

            key = (name, tuple(sorted(indices)))
            if key in seen:
                continue
            seen.add(key)

            authors.append(
                {
                    "name": name,
                    "indices": indices,
                }
            )

    return authors


def build_institutions_from_elements(
    elements: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Construit la liste des institutions à partir des éléments typés institution/indice.
    On regroupe par line_id, on identifie l'indice, puis on concatène le texte institution.
    """
    by_line = group_by_line(elements)
    index_to_text: Dict[int, List[str]] = {}

    for lid, line_elems in by_line.items():
        # indice = élément dont element_type == "indice"
        idx_values: List[int] = []
        for e in line_elems:
            if e.get("element_type") == "indice":
                try:
                    val = int(e.get("text", "").strip())
                    idx_values.append(val)
                except ValueError:
                    continue

        if not idx_values:
            # pas d'indice explicite sur cette ligne -> on ignore pour les institutions
            continue

        # on prend le premier indice (cas standard)
        inst_index = idx_values[0]

        # texte institution = concat des éléments element_type == "institution"
        inst_text_elems = [e for e in line_elems if e.get("element_type") == "institution"]
        text = concat_text(inst_text_elems)
        if not text:
            continue

        index_to_text.setdefault(inst_index, []).append(text)

    # fusion par index
    institutions: List[Dict[str, Any]] = []
    for idx in sorted(index_to_text.keys()):
        full_text = " ".join(index_to_text[idx]).strip()
        institutions.append(
            {
                "index": idx,
                "text": full_text,
            }
        )

    return institutions


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

SECTION_LABEL_TYPES = [
    "section_background_and_aims",
    "section_materials_and_methods",
    "section_results",
    "section_conclusion",
    "section_disclosure",
]

SECTION_NAME_MAP = {
    "section_background_and_aims": "background_and_aims",
    "section_materials_and_methods": "materials_and_methods",
    "section_results": "results",
    "section_conclusion": "conclusion",
    "section_disclosure": "disclosure_text",
}


def build_sections_for_abstract(
    abstract_elements: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Construit un dict sections[section_name] = texte concaténé
    à partir des labels section_* et des textes section_*_text + abstract_text
    dans les intervalles [label, prochain label[.
    """
    sections: Dict[str, str] = {}

    # On trie tous les éléments de cet abstract par ordre global
    elems_sorted = sorted(abstract_elements, key=element_order_key)

    # Récupérer tous les labels de section dans cet abstract
    section_labels: List[Dict[str, Any]] = [
        e for e in elems_sorted
        if e.get("element_type") in SECTION_LABEL_TYPES
    ]
    # Déjà triés par order_key mais on sécurise sur id pour éviter les surprises
    section_labels.sort(key=lambda e: e.get("id", 0))

    if not section_labels:
        return sections

    # Préparer un accès par id
    id_to_index = {e["id"]: idx for idx, e in enumerate(elems_sorted) if "id" in e}

    for i, label in enumerate(section_labels):
        label_type = label.get("element_type")
        if label_type not in SECTION_NAME_MAP:
            continue

        section_name = SECTION_NAME_MAP[label_type]
        label_id = label.get("id")
        if label_id is None:
            continue

        start_idx = id_to_index.get(label_id)
        if start_idx is None:
            continue

        if i < len(section_labels) - 1:
            next_label = section_labels[i + 1]
            next_id = next_label.get("id")
            if next_id is None:
                end_idx = len(elems_sorted) - 1
            else:
                end_idx = id_to_index.get(next_id, len(elems_sorted)) - 1
        else:
            # dernière section : jusqu'à la fin de l'abstract
            end_idx = len(elems_sorted) - 1

        # Récupérer tous les éléments texte de cette section :
        #    - section_<X>_text
        #    - abstract_text (texte résiduel dans la même zone)
        section_text_parts: List[str] = []

        for k in range(start_idx + 1, end_idx + 1):
            e = elems_sorted[k]
            if e.get("type") != "text":
                continue

            etype = e.get("element_type")
            if etype == f"{label_type}_text" or etype == "abstract_text":
                txt = e.get("text", "")
                if txt:
                    section_text_parts.append(txt)

        full_text = " ".join(section_text_parts).strip()
        if full_text:
            sections[section_name] = full_text

    return sections


# ---------------------------------------------------------------------------
# Construction d'un abstract structuré
# ---------------------------------------------------------------------------

def build_abstract_object(abstract_id: str, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Construit l'objet métier pour un abstract donné.
    """
    # Tri global
    elems_sorted = sorted(elements, key=element_order_key)

    # Page start / end
    pages = [e.get("page", 0) for e in elems_sorted if isinstance(e, dict) and "page" in e]
    page_start = min(pages) if pages else None
    page_end = max(pages) if pages else None

    # Code abstract
    abstract_code = None
    for e in elems_sorted:
        if e.get("element_type") == "code_abstract":
            abstract_code = e.get("text", "").strip()
            break

    # Titre : concat de tous les abstract_title
    title_elems = [e for e in elems_sorted if e.get("element_type") == "abstract_title"]
    title = concat_text(title_elems) if title_elems else ""

    # Auteurs : lignes author_title + author
    author_elems = [e for e in elems_sorted if e.get("element_type") in ("author_title", "author")]
    authors_by_line = group_by_line(author_elems)
    author_line_texts: List[str] = []
    for lid, line_elems in authors_by_line.items():
        author_line_texts.append(concat_text(line_elems))
    authors = parse_authors_from_lines(author_line_texts)

    # Institutions
    institution_elems = [e for e in elems_sorted if e.get("element_type") == "institution" or e.get("element_type") == "indice"]
    institutions = build_institutions_from_elements(institution_elems)

    # Sections (inclut disclosure_text)
    sections = build_sections_for_abstract(elems_sorted)

    abstract_obj: Dict[str, Any] = {
        "abstract_id": abstract_id,
        "abstract_code": abstract_code,
        "page_start": page_start,
        "page_end": page_end,
        "title": title,
        "authors": authors,
        "institutions": institutions,
        "sections": sections,
    }

    return abstract_obj


# ---------------------------------------------------------------------------
# Pipeline fichier complet
# ---------------------------------------------------------------------------

def process_file(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier JSON d'entrée introuvable : {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Racine = dict avec "elements"
    if not isinstance(data, dict) or "elements" not in data:
        raise ValueError("Le JSON d'entrée doit être un dict avec une clé 'elements'.")

    elements = data["elements"]
    if not isinstance(elements, list):
        raise ValueError("Le champ 'elements' doit être une liste.")

    # Regrouper les éléments par abstract_id
    abstracts_elements: Dict[str, List[Dict[str, Any]]] = {}
    for e in elements:
        if not isinstance(e, dict):
            continue
        abs_id = e.get("abstract_id")
        if not abs_id:
            continue
        abstracts_elements.setdefault(abs_id, []).append(e)

    # Construire les objets abstracts
    abstracts: List[Dict[str, Any]] = []
    for abs_id in sorted(abstracts_elements.keys()):
        abs_elems = abstracts_elements[abs_id]
        abstract_obj = build_abstract_object(abs_id, abs_elems)
        abstracts.append(abstract_obj)

    # Sauvegarde
    output_data = {
        "abstracts": abstracts
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Passe 3 : agrégation par abstract à partir des éléments typés (pass2)."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Fichier JSON en entrée (sortie de semantic_typing_pass_2.py).",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Fichier JSON de sortie avec les abstracts agrégés.",
    )

    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    process_file(input_path, output_path)


if __name__ == "__main__":
    main()
