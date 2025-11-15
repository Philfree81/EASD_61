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
        * section_*_text
        * section_supported_by / section_supported_by_text
        * section_clinical_trial_registration_number /
          section_clinical_trial_registration_number_text
        * section_disclosure / section_disclosure_text
        * abstract_text
        * image / table / image_text
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constantes de signatures
# ---------------------------------------------------------------------------

TITLE_SIGNATURES = {
    "STIX-Bold_8.5_20",
}

AUTHOR_FONT = "STIX-Regular_8.5_4"

ABSTRACT_TEXT_SIGNATURES = {
    "STIX-Regular_8.5_4",
    "STIX-BoldItalic_8.5_22",
    "SymbolMT_8.5_0",
}

# Polices utilisées pour les légendes / texte d'image
IMAGE_TEXT_SIGNATURES = {
    "STIX-Italic_8.5_6",
}

# Types de sections reconnues (labels de sections)
SECTION_TYPES = {
    "section_background_and_aims",
    "section_materials_and_methods",
    "section_results",
    "section_conclusion",
    "section_supported_by",
    "section_clinical_trial_registration_number",
    "section_disclosure",
}


# ---------------------------------------------------------------------------


def group_by_line(elements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
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
    def line_key(lid: str) -> Tuple[int, int]:
        elems = lines[lid]
        page = min(e.get("page", 0) for e in elems)
        line_num = min(e.get("line_num", 0) for e in elems)
        return (page, line_num)
    return sorted(lines.keys(), key=line_key)


def get_index_by_id(elements: List[Dict[str, Any]]) -> Dict[int, int]:
    mapping: Dict[int, int] = {}
    for idx, e in enumerate(elements):
        if not isinstance(e, dict):
            continue
        eid = e.get("id")
        if isinstance(eid, int):
            mapping[eid] = idx
    return mapping


def concat_line_text(line_elems: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for e in line_elems:
        if e.get("type") == "text":
            txt = e.get("text", "")
            if txt:
                parts.append(txt)
    return " ".join(parts).strip()


def has_section_label(line_elems: List[Dict[str, Any]]) -> bool:
    return any(e.get("element_type") in SECTION_TYPES for e in line_elems)


def element_global_key(e: Dict[str, Any]) -> Tuple[int, int, float, int]:
    page = e.get("page", 0)
    line_num = e.get("line_num", 0)
    x = e.get("position", {}).get("x", 0.0)
    eid = e.get("id", 0)
    return (page, line_num, x, eid)


# ---------------------------------------------------------------------------
# Spans d'abstracts
# ---------------------------------------------------------------------------


def compute_abstract_spans(elements: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], int, int]]:
    """Repère les blocs d'abstracts entre code_abstract successifs."""
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

    # 1) Marquer abstract_id sur tous les éléments du span
    for i in range(span_start, span_end + 1):
        e = elements[i]
        if isinstance(e, dict):
            e["abstract_id"] = abstract_id

    span_elems = [e for e in elements[span_start: span_end + 1] if isinstance(e, dict)]

    # Lignes globales (toutes colonnes) pour tout l'abstract
    all_lines = group_by_line(span_elems)
    all_ordered_line_ids = sort_line_ids(all_lines)
    all_line_index_map = {lid: idx for idx, lid in enumerate(all_ordered_line_ids)}

    # Colonne principale (celle du code) pour repérer titre / auteurs
    code_column = code_elem.get("line_position")
    code_page = code_elem.get("page", 0)
    code_id = code_elem.get("id", -1)

    column_elems_after_code: List[Dict[str, Any]] = []
    for e in span_elems:
        if e.get("line_position") != code_column:
            continue
        page = e.get("page", 0)
        eid = e.get("id", -1)
        if page > code_page or (page == code_page and eid > code_id):
            column_elems_after_code.append(e)

    if not column_elems_after_code:
        return

    lines = group_by_line(column_elems_after_code)
    if not lines:
        return

    ordered_line_ids = sort_line_ids(lines)
    line_index_map = {lid: idx for idx, lid in enumerate(ordered_line_ids)}

    # -----------------------------------------------------------------------
    # En-tête avant sections (dans la colonne du code)
    # -----------------------------------------------------------------------
    header_line_ids: List[str] = []
    for lid in ordered_line_ids:
        line_elems = lines[lid]
        if has_section_label(line_elems):
            break
        header_line_ids.append(lid)

    if not header_line_ids:
        return

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
    # abstract_title / author_title
    # -----------------------------------------------------------------------
    title_candidates_by_lid: Dict[str, List[Dict[str, Any]]] = {}
    author_title_line_id: Optional[str] = None

    for idx, info in enumerate(header_infos):
        lid = info["lid"]
        if not info["has_title_font"]:
            break

        for e in info["text_elems"]:
            if e.get("element_type") is None and e.get("signature") in TITLE_SIGNATURES:
                title_candidates_by_lid.setdefault(lid, []).append(e)

        if author_title_line_id is None and info["line_start"] and idx + 1 < len(header_infos):
            next_info = header_infos[idx + 1]
            if not next_info["has_title_font"] and next_info["has_author_font"]:
                author_title_line_id = lid

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
    # Auteurs supplémentaires (colonne du code, via ';')
    # -----------------------------------------------------------------------
    semicolon_line_idx: Optional[int] = None
    semicolon_line_id: Optional[str] = None

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
                semicolon_line_id = lid
                break

        if semicolon_line_idx is not None:
            # marquer les auteurs dans la colonne principale
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

            # rattrapage : tout AUTHOR_FONT non typé dans la zone auteurs
            for j in range(start_idx, semicolon_line_idx + 1):
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
    # Marquage des labels "Supported by:" et
    # "Clinical Trial Registration Number:"
    # -----------------------------------------------------------------------
    for e in span_elems:
        if (
            e.get("type") == "text"
            and e.get("element_type") is None
            and e.get("signature") in IMAGE_TEXT_SIGNATURES
        ):
            txt = (e.get("text") or "").strip()
            txt_norm = txt.lower().replace("\u00a0", " ")
            if txt_norm.startswith("supported by:"):
                e["element_type"] = "section_supported_by"
            elif txt_norm.startswith("clinical trial registration number:"):
                e["element_type"] = "section_clinical_trial_registration_number"

    # -----------------------------------------------------------------------
    # Institutions (toutes colonnes, basé sur indice + AUTHOR_FONT)
    # -----------------------------------------------------------------------
    # 1) repérer la première section dans l'ordre global
    first_section_global_idx: Optional[int] = None
    for idx, lid in enumerate(all_ordered_line_ids):
        if has_section_label(all_lines[lid]):
            first_section_global_idx = idx
            break

    # 2) déterminer où commence la fenêtre d'institutions
    if semicolon_line_id is not None and semicolon_line_id in all_line_index_map:
        institutions_start_idx = all_line_index_map[semicolon_line_id] + 1
    else:
        # pas de ';' trouvé : on autorise à démarrer le bloc institutions
        # dès la première ligne (avant section) qui ressemble à "indice + AUTHOR_FONT"
        institutions_start_idx = 0

    in_institution_block = False

    for j in range(institutions_start_idx, len(all_ordered_line_ids)):
        lid = all_ordered_line_ids[j]
        line_elems = all_lines[lid]

        # arrêt sur première section (sauf si on n'a jamais démarré le bloc)
        if has_section_label(line_elems):
            if in_institution_block:
                break
            else:
                # si on n'a pas encore d'institutions, on arrête aussi :
                break

        # si on a une limite de section connue et qu'on la dépasse, on ne traite plus
        if first_section_global_idx is not None and j >= first_section_global_idx and in_institution_block:
            break

        text_elems_sorted = sorted(
            [e for e in line_elems if e.get("type") == "text"],
            key=lambda e: e.get("position", {}).get("x", 0.0),
        )
        if not text_elems_sorted:
            if in_institution_block:
                # ligne vide après institutions => on arrête
                break
            continue

        has_indice = any(e.get("element_type") == "indice" for e in text_elems_sorted)
        has_author_font = any(
            e.get("signature") == AUTHOR_FONT and e.get("type") == "text"
            for e in text_elems_sorted
        )

        # 2.a Démarrage "robuste" : ligne avec indice + AUTHOR_FONT
        if has_indice and has_author_font and not in_institution_block:
            in_institution_block = True
            for e in text_elems_sorted:
                if (
                    e.get("type") == "text"
                    and e.get("signature") == AUTHOR_FONT
                    and e.get("element_type") is None
                ):
                    e["element_type"] = "institution"
            continue

        # 2.b Si on n'a pas encore démarré et pas le pattern fort, on saute
        if not in_institution_block:
            continue

        # 2.c Bloc institutions déjà démarré : toutes les lignes avant section
        #     avec AUTHOR_FONT deviennent des institutions (même sans indice)
        if has_author_font:
            for e in text_elems_sorted:
                if (
                    e.get("type") == "text"
                    and e.get("signature") == AUTHOR_FONT
                    and e.get("element_type") is None
                ):
                    e["element_type"] = "institution"
            continue

        # 2.d Ligne sans AUTHOR_FONT dans un bloc institutions => fin probable
        #     (changement de nature de contenu)
        if in_institution_block:
            break

    # -----------------------------------------------------------------------
    # Sections (sections classiques + supported_by + clinical_trial + disclosure)
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

            # Disclosure : tout texte non typé dans la zone
            if label_type == "section_disclosure":
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

            # Supported by : tout texte non typé dans la zone
            if label_type == "section_supported_by":
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
                    e["element_type"] = "section_supported_by_text"
                continue

            # Clinical Trial Registration Number : tout texte non typé dans la zone
            if label_type == "section_clinical_trial_registration_number":
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
                    e["element_type"] = "section_clinical_trial_registration_number_text"
                continue

            # autres sections : section_*_text + abstract_text
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
                elements[idx]["element_type"] = target_type

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
    # Images / tables / image_text
    # -----------------------------------------------------------------------
    images: List[Dict[str, Any]] = []
    for e in span_elems:
        if e.get("type") == "image":
            if e.get("element_type") is None:
                e["element_type"] = "image"
            images.append(e)
        elif e.get("type") == "table":
            if e.get("element_type") is None:
                e["element_type"] = "table"

    # Texte de légende sous les images -> image_text
    for img in images:
        page = img.get("page", 0)
        pos = img.get("position", {})
        x_img = pos.get("x", 0.0)
        w_img = pos.get("w", 0.0)
        y_img = pos.get("y", 0.0)
        h_img = pos.get("h", 0.0)
        bottom = y_img + h_img
        margin = 60.0
        eps = 2.0

        for e in span_elems:
            if e.get("type") != "text":
                continue
            if e.get("element_type") is not None:
                continue
            if e.get("signature") not in IMAGE_TEXT_SIGNATURES:
                continue
            if e.get("page", 0) != page:
                continue
            epos = e.get("position", {})
            y = epos.get("y", 0.0)
            x = epos.get("x", 0.0)
            if not (bottom - eps <= y <= bottom + margin + eps):
                continue
            if not (x_img - 5 <= x <= x_img + w_img + 5):
                continue
            e["element_type"] = "image_text"


# ---------------------------------------------------------------------------
# Pipeline global
# ---------------------------------------------------------------------------


def process_file(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier JSON d'entrée introuvable : {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or "elements" not in data:
        raise ValueError("Le JSON d'entrée doit être un dict contenant 'elements'.")

    elements = data["elements"]
    if not isinstance(elements, list):
        raise ValueError("Le champ 'elements' doit être une liste.")

    if not elements:
        raise ValueError("Aucun élément trouvé dans le JSON d'entrée.")

    # tri géométrique global
    elements.sort(
        key=lambda e: element_global_key(e) if isinstance(e, dict) else (0, 0, 0.0, 0)
    )

    # spans d'abstracts (basés sur code_abstract)
    spans = compute_abstract_spans(elements)

    # traitement des abstracts
    for abs_idx, (code_elem, span_start, span_end) in enumerate(spans, start=1):
        if not isinstance(code_elem, dict):
            continue
        abstract_id = f"abs_{abs_idx:04d}"
        process_single_abstract(elements, code_elem, span_start, span_end, abstract_id)

    data["elements"] = elements
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Passe 2 : typage contextuel des éléments d'un abstract."
    )
    parser.add_argument("-i", "--input", required=True, help="JSON entrée (pass1).")
    parser.add_argument("-o", "--output", required=True, help="JSON sortie (pass2).")
    args = parser.parse_args()

    process_file(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
