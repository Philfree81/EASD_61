#!/usr/bin/env python3
# semantic_typing_pass_2.py
"""
Passe 2 : typage contextuel des éléments d'un abstract.

Entrée :
    - JSON produit par la passe 1 (semantic_typing_pass_1.py)
      contenant déjà notamment :
        * code_abstract
        * section_* (labels, y compris section_disclosure)
        * header, footer, indice, symbol_text, etc.

Sortie :
    - même JSON, avec pour chaque élément d'abstract :
        * abstract_id
        * abstract_title
        * author_title
        * author
        * institution
        * section_*_text (background, methods, results, conclusion, disclosure)
        * abstract_text (texte "résiduel" dans les zones de sections)
        * image / table pour les blocs non textuels
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constantes de signatures
# ---------------------------------------------------------------------------

# Police(s) de titre
TITLE_SIGNATURES = {
    "STIX-Bold_8.5_20",
}

# Police principale du corps de texte des abstracts / auteurs / institutions
AUTHOR_FONT = "STIX-Regular_8.5_4"

# Polices considérées comme texte de corps dans les sections
ABSTRACT_TEXT_SIGNATURES = {
    "STIX-Regular_8.5_4",
    "STIX-BoldItalic_8.5_22",
    "SymbolMT_8.5_0",
}

# Types de sections reconnues (labels créés en pass1)
SECTION_TYPES = {
    "section_background_and_aims",
    "section_materials_and_methods",
    "section_results",
    "section_conclusion",
    "section_disclosure",  # ajout pour la disclosure
}

# ---------------------------------------------------------------------------


def group_by_line(elements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Regroupe une liste d'éléments par line_id.
    """
    lines: Dict[str, List[Dict[str, Any]]] = {}
    for e in elements:
        if not isinstance(e, dict):
            continue
        lid = e.get("line_id")
        if lid is None:
            continue
        lines.setdefault(lid, []).append(e)
    return lines


def sort_line_ids(lines: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """
    Trie les line_id dans l'ordre logique :
        - par page
        - puis par line_num minimal sur cette ligne
    """
    def line_key(lid: str) -> Tuple[int, int]:
        elems = lines[lid]
        page = min(e.get("page", 0) for e in elems)
        line_num = min(e.get("line_num", 0) for e in elems)
        return (page, line_num)

    return sorted(lines.keys(), key=line_key)


def get_index_by_id(elements: List[Dict[str, Any]]) -> Dict[int, int]:
    """
    Mapping id -> index dans la liste elements.
    """
    mapping: Dict[int, int] = {}
    for idx, e in enumerate(elements):
        if not isinstance(e, dict):
            continue
        eid = e.get("id")
        if isinstance(eid, int):
            mapping[eid] = idx
    return mapping


def concat_line_text(line_elems: List[Dict[str, Any]]) -> str:
    """
    Concatène le texte des éléments textuels d'une ligne.
    """
    parts: List[str] = []
    for e in line_elems:
        if e.get("type") == "text":
            txt = e.get("text", "")
            if txt:
                parts.append(txt)
    return " ".join(parts).strip()


def has_section_label(line_elems: List[Dict[str, Any]]) -> bool:
    """
    True si la ligne contient un label de section (background, results, disclosure, etc.).
    """
    for e in line_elems:
        if e.get("element_type") in SECTION_TYPES:
            return True
    return False


# ---------------------------------------------------------------------------
# Détection des spans d'abstracts
# ---------------------------------------------------------------------------


def compute_abstract_spans(elements: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], int, int]]:
    """
    Identifie les spans [start_idx, end_idx] correspondant à chaque abstract,
    à partir des éléments de type code_abstract.

    Retourne une liste de tuples :
        (code_elem, start_index, end_index)
    """
    code_indices: List[int] = []
    for idx, e in enumerate(elements):
        if not isinstance(e, dict):
            continue
        if e.get("element_type") == "code_abstract":
            code_indices.append(idx)

    spans: List[Tuple[Dict[str, Any], int, int]] = []

    if not code_indices:
        return spans

    for i, code_idx in enumerate(code_indices):
        start_idx = code_idx
        if i < len(code_indices) - 1:
            end_idx = code_indices[i + 1] - 1
        else:
            end_idx = len(elements) - 1
        spans.append((elements[code_idx], start_idx, end_idx))

    return spans


# ---------------------------------------------------------------------------
# Traitement d'un abstract
# ---------------------------------------------------------------------------


def process_single_abstract(
    elements: List[Dict[str, Any]],
    code_elem: Dict[str, Any],
    span_start: int,
    span_end: int,
    abstract_id: str,
) -> None:
    """
    Enrichit les éléments d'un abstract :
        - abstract_id
        - abstract_title
        - author_title
        - author
        - institution
        - section_*_text
        - abstract_text
        - image / table
    """

    # 1) Marquer tous les éléments du span avec abstract_id
    for i in range(span_start, span_end + 1):
        e = elements[i]
        if isinstance(e, dict):
            e["abstract_id"] = abstract_id

    # Sous-liste utile
    span_elems = [e for e in elements[span_start: span_end + 1] if isinstance(e, dict)]

    # Colonne (left/right) de l'abstract
    code_column = code_elem.get("line_position")

    # On ne garde que les éléments de la même colonne, après le code_abstract
    column_elems_after_code: List[Dict[str, Any]] = []
    code_page = code_elem.get("page", 0)
    code_id = code_elem.get("id", -1)

    for e in span_elems:
        if e.get("line_position") != code_column:
            continue
        page = e.get("page", 0)
        eid = e.get("id", -1)
        if page > code_page or (page == code_page and eid > code_id):
            column_elems_after_code.append(e)

    if not column_elems_after_code:
        return

    # Regroupement par ligne
    lines = group_by_line(column_elems_after_code)
    if not lines:
        return

    ordered_line_ids = sort_line_ids(lines)
    line_index_map = {lid: idx for idx, lid in enumerate(ordered_line_ids)}

    # -----------------------------------------------------------------------
    # 2) Détection des lignes d'en-tête (avant la 1ère section)
    # -----------------------------------------------------------------------
    header_line_ids: List[str] = []
    for lid in ordered_line_ids:
        line_elems = lines[lid]
        if has_section_label(line_elems):
            break
        header_line_ids.append(lid)

    if not header_line_ids:
        return

    # Pré-calcul d'infos par ligne d'en-tête
    header_infos: List[Dict[str, Any]] = []
    for lid in header_line_ids:
        line_elems = lines[lid]
        text_elems = [e for e in line_elems if e.get("type") == "text"]
        signatures = {e.get("signature") for e in text_elems}
        has_title_font = any(sig in TITLE_SIGNATURES for sig in signatures)
        has_author_font = any(sig == AUTHOR_FONT for sig in signatures)
        line_start_flag = any(e.get("line_start") for e in line_elems)
        header_infos.append(
            {
                "lid": lid,
                "line_elems": line_elems,
                "text_elems": text_elems,
                "signatures": signatures,
                "has_title_font": has_title_font,
                "has_author_font": has_author_font,
                "line_start": line_start_flag,
            }
        )

    # -----------------------------------------------------------------------
    # 3) abstract_title et author_title
    # -----------------------------------------------------------------------
    title_candidates_by_lid: Dict[str, List[Dict[str, Any]]] = {}
    author_title_line_id: Optional[str] = None

    # 3.1 bloc de lignes en police titre ; l'auteur_titre est la dernière de ce bloc
    for idx, info in enumerate(header_infos):
        lid = info["lid"]

        if not info["has_title_font"]:
            break

        # candidats "abstract_title"
        for e in info["text_elems"]:
            if e.get("element_type") is None and e.get("signature") in TITLE_SIGNATURES:
                title_candidates_by_lid.setdefault(lid, []).append(e)

        # auteur_titre : démarre la ligne, suivie d'une ligne non-titre avec AUTHOR_FONT
        if author_title_line_id is None and info["line_start"] and idx + 1 < len(header_infos):
            next_info = header_infos[idx + 1]
            if not next_info["has_title_font"] and next_info["has_author_font"]:
                author_title_line_id = lid

    # 3.2 Fallback : s'il n'y a pas de bloc "même police", on prend la 1ère ligne avec AUTHOR_FONT
    if author_title_line_id is None:
        for info in header_infos:
            if info["has_author_font"]:
                author_title_line_id = info["lid"]
                break
        if author_title_line_id is not None and not title_candidates_by_lid:
            for info in header_infos:
                lid = info["lid"]
                for e in info["text_elems"]:
                    if e.get("element_type") is None and e.get("signature") in TITLE_SIGNATURES:
                        title_candidates_by_lid.setdefault(lid, []).append(e)
                if info["has_author_font"]:
                    break

    # 3.3 marquage des titres
    for lid, elems in title_candidates_by_lid.items():
        if lid == author_title_line_id:
            continue
        for e in elems:
            if e.get("element_type") is None:
                e["element_type"] = "abstract_title"

    if author_title_line_id is not None:
        for e in lines[author_title_line_id]:
            if (
                e.get("type") == "text"
                and e.get("element_type") is None
                and e.get("signature") in TITLE_SIGNATURES
            ):
                e["element_type"] = "author_title"

    # -----------------------------------------------------------------------
    # 4) Auteurs supplémentaires
    # -----------------------------------------------------------------------
    semicolon_line_idx: Optional[int] = None
    if author_title_line_id is not None:
        start_idx = line_index_map[author_title_line_id]
        for j in range(start_idx, len(ordered_line_ids)):
            lid = ordered_line_ids[j]
            line_elems = lines[lid]
            if has_section_label(line_elems):
                break
            line_txt = concat_line_text(line_elems)
            if ";" in line_txt:
                semicolon_line_idx = j
                break

        if semicolon_line_idx is not None:
            # Lignes d'auteurs entre author_title et la ligne du ';'
            for j in range(start_idx + 1, semicolon_line_idx + 1):
                lid = ordered_line_ids[j]
                line_elems = lines[lid]
                if has_section_label(line_elems):
                    break
                for e in line_elems:
                    if (
                        e.get("type") == "text"
                        and e.get("element_type") is None
                        and e.get("signature") == AUTHOR_FONT
                    ):
                        e["element_type"] = "author"

    # Rattrapage : on marque en author tout AUTHOR_FONT non typé dans la zone auteurs
    if author_title_line_id is not None and semicolon_line_idx is not None:
        idx_start = line_index_map[author_title_line_id]
        for j in range(idx_start, semicolon_line_idx + 1):
            lid = ordered_line_ids[j]
            line_elems = lines[lid]
            if has_section_label(line_elems):
                break
            for e in line_elems:
                if (
                    e.get("type") == "text"
                    and e.get("element_type") is None
                    and e.get("signature") == AUTHOR_FONT
                ):
                    e["element_type"] = "author"

    # -----------------------------------------------------------------------
    # 5) Institutions
    # -----------------------------------------------------------------------
    if semicolon_line_idx is not None:
        institutions_start_idx = semicolon_line_idx + 1
        in_institution_block = False

        for j in range(institutions_start_idx, len(ordered_line_ids)):
            lid = ordered_line_ids[j]
            line_elems = lines[lid]

            if has_section_label(line_elems):
                break

            text_elems_sorted = sorted(
                [e for e in line_elems if e.get("type") == "text"],
                key=lambda e: e.get("position", {}).get("x", 0.0),
            )
            if not text_elems_sorted:
                if in_institution_block:
                    break
                continue

            first_text = text_elems_sorted[0]

            if first_text.get("element_type") == "indice":
                # Cas standard : indice en début de ligne
                in_institution_block = True
                for e in text_elems_sorted:
                    if e.get("element_type") is None and e.get("type") == "text":
                        e["element_type"] = "institution"
                continue

            if in_institution_block:
                # Ligne de continuation (ex: "USA,")
                for e in text_elems_sorted:
                    if (
                        e.get("element_type") is None
                        and e.get("type") == "text"
                        and e.get("signature") == AUTHOR_FONT
                    ):
                        e["element_type"] = "institution"
                continue

            # Hors bloc institutions et sans indice en tête : on s'arrête
            break

    # -----------------------------------------------------------------------
    # 6) Sections : section_*_text + abstract_text
    # -----------------------------------------------------------------------
    section_labels = [e for e in span_elems if e.get("element_type") in SECTION_TYPES]
    section_labels.sort(key=lambda e: e.get("id", 0))

    if section_labels:
        id_to_index = get_index_by_id(elements)

        for i, label in enumerate(section_labels):
            label_type = label.get("element_type")
            label_id = label.get("id")
            if label_id is None:
                continue
            label_idx = id_to_index.get(label_id)
            if label_idx is None:
                continue

            if i < len(section_labels) - 1:
                next_label = section_labels[i + 1]
                next_label_id = next_label.get("id")
                if next_label_id is None:
                    section_end_idx = span_end
                else:
                    next_idx = id_to_index.get(next_label_id, span_end + 1)
                    section_end_idx = min(next_idx - 1, span_end)
            else:
                section_end_idx = span_end

            if label_type == "section_disclosure":
                # Disclosure : tout texte non typé dans la zone
                for idx in range(label_idx + 1, section_end_idx + 1):
                    e = elements[idx]
                    if not isinstance(e, dict):
                        continue
                    if e.get("abstract_id") != abstract_id:
                        continue
                    if e.get("type") != "text":
                        continue
                    if e.get("element_type") is not None:
                        continue
                    e["element_type"] = "section_disclosure_text"
                continue

            # Autres sections : section_*_text + abstract_text
            section_text_indices: List[int] = []
            for idx in range(label_idx + 1, section_end_idx + 1):
                e = elements[idx]
                if not isinstance(e, dict):
                    continue
                if e.get("abstract_id") != abstract_id:
                    continue
                if e.get("type") != "text":
                    continue
                if e.get("element_type") is not None:
                    continue
                if e.get("signature") == AUTHOR_FONT:
                    section_text_indices.append(idx)

            target_type = f"{label_type}_text"
            for idx in section_text_indices:
                e = elements[idx]
                e["element_type"] = target_type

            # Texte résiduel dans la zone → abstract_text
            for idx in range(label_idx + 1, section_end_idx + 1):
                e = elements[idx]
                if not isinstance(e, dict):
                    continue
                if e.get("abstract_id") != abstract_id:
                    continue
                if e.get("type") != "text":
                    continue
                if e.get("element_type") is not None:
                    continue
                if e.get("signature") not in ABSTRACT_TEXT_SIGNATURES:
                    continue
                e["element_type"] = "abstract_text"

    # -----------------------------------------------------------------------
    # 7) Image / table
    # -----------------------------------------------------------------------
    for e in span_elems:
        if e.get("type") == "image" and e.get("element_type") is None:
            e["element_type"] = "image"
        if e.get("type") == "table" and e.get("element_type") is None:
            e["element_type"] = "table"


# ---------------------------------------------------------------------------
# Pipeline global
# ---------------------------------------------------------------------------


def process_file(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier JSON d'entrée introuvable : {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or "elements" not in data:
        raise ValueError("Le JSON d'entrée doit être un dict contenant une clé 'elements'.")

    elements = data["elements"]
    if not isinstance(elements, list):
        raise ValueError("Le champ 'elements' doit être une liste.")

    if not elements:
        raise ValueError("Aucun élément trouvé dans le JSON d'entrée.")

    # On trie par id pour retrouver l'ordre PyMuPDF
    elements.sort(key=lambda e: e.get("id", 0) if isinstance(e, dict) else 0)

    spans = compute_abstract_spans(elements)

    for abs_idx, (code_elem, span_start, span_end) in enumerate(spans, start=1):
        if not isinstance(code_elem, dict):
            continue
        abstract_id = f"abs_{abs_idx:04d}"
        process_single_abstract(elements, code_elem, span_start, span_end, abstract_id)

    # Sauvegarde
    data["elements"] = elements
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Passe 2 : typage contextuel des éléments d'un abstract."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Fichier JSON en entrée (sortie de semantic_typing_pass_1.py).",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Fichier JSON de sortie avec typage contextuel enrichi.",
    )

    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    process_file(input_path, output_path)


if __name__ == "__main__":
    main()
