#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Constantes de polices / types --- #

TITLE_SIGNATURES = {
    "STIX-Bold_8.5_20",
}

# Police des auteurs ET des institutions
AUTHOR_FONT = "STIX-Regular_8.5_4"

# Polices acceptées pour du texte scientifique "neutre" (hors gras titre)
ABSTRACT_TEXT_SIGNATURES = {
    "STIX-Regular_8.5_4",
    "STIX-BoldItalic_8.5_22",
    "SymbolMT_8.5_0",
}

# Polices des blocs en italique sous image / funding / trial number
IMAGE_TEXT_SIGNATURES = {
    "STIX-Italic_8.5_6",
}

# Types de sections "scientifiques"
SECTION_TYPES = {
    "section_background_and_aims",
    "section_materials_and_methods",
    "section_results",
    "section_conclusion",
    "section_supported_by",
    "section_clinical_trial_registration_number",
    "section_disclosure",
}


# --- Utilitaires --- #

def group_by_line(elements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Regroupe les éléments par line_id."""
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
    """Trie les line_id par (page, line_num) croissants."""
    def line_key(lid: str) -> Tuple[int, int]:
        elems = lines[lid]
        page = min(e.get("page", 0) for e in elems)
        line_num = min(e.get("line_num", 0) for e in elems)
        return (page, line_num)

    return sorted(lines.keys(), key=line_key)


def get_index_by_id(elements: List[Dict[str, Any]]) -> Dict[int, int]:
    """Map id -> index dans la liste elements."""
    mapping: Dict[int, int] = {}
    for idx, e in enumerate(elements):
        if not isinstance(e, dict):
            continue
        eid = e.get("id")
        if isinstance(eid, int):
            mapping[eid] = idx
    return mapping


def concat_line_text(line_elems: List[Dict[str, Any]]) -> str:
    """Concatène les textes d'une ligne en une seule string (séparée par des espaces)."""
    parts: List[str] = []
    for e in line_elems:
        if e.get("type") == "text":
            txt = e.get("text", "")
            if txt:
                parts.append(txt)
    return " ".join(parts).strip()


def has_section_label(line_elems: List[Dict[str, Any]]) -> bool:
    """True si la ligne contient au moins un élément de type section_*."""
    return any(e.get("element_type") in SECTION_TYPES for e in line_elems)


def element_global_key(e: Dict[str, Any]) -> Tuple[int, int, float, int]:
    """Clé de tri globale : (page, line_num, x, id)."""
    page = e.get("page", 0)
    line_num = e.get("line_num", 0)
    x = e.get("position", {}).get("x", 0.0)
    eid = e.get("id", 0)
    return (page, line_num, x, eid)


# --- Détection des spans d'abstracts --- #

def compute_abstract_spans(
    elements: List[Dict[str, Any]]
) -> List[Tuple[Dict[str, Any], int, int]]:
    """
    Retourne une liste de tuples (code_abstract_element, start_idx, end_idx),
    où start_idx/end_idx délimitent les éléments appartenant à chaque abstract.
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


# --- Traitement d'un abstract --- #

def process_single_abstract(
    elements: List[Dict[str, Any]],
    code_elem: Dict[str, Any],
    span_start: int,
    span_end: int,
    abstract_id: str,
) -> None:
    """
    Typage sémantique des éléments appartenant à un abstract donné.
    """

    # 1) Marquage de l'abstract_id pour les éléments du span
    for i in range(span_start, span_end + 1):
        e = elements[i]
        if isinstance(e, dict):
            e["abstract_id"] = abstract_id

    span_elems = [e for e in elements[span_start:span_end + 1] if isinstance(e, dict)]
    if not span_elems:
        return

    # Groupement par lignes (les deux colonnes)
    all_lines = group_by_line(span_elems)
    all_ordered_line_ids = sort_line_ids(all_lines)
    all_line_index_map = {lid: idx for idx, lid in enumerate(all_ordered_line_ids)}

    # Colonne du code abstract
    code_column = code_elem.get("line_position")
    code_page = code_elem.get("page", 0)
    code_id = code_elem.get("id", -1)

    # On ne regarde que les éléments de la même colonne que le code,
    # après la ligne du code.
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

    # 2) En-tête (header) dans la colonne du code : jusqu'à la première section
    header_line_ids: List[str] = []
    for lid in ordered_line_ids:
        if has_section_label(lines[lid]):
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
            dict(
                lid=lid,
                line_elems=line_elems,
                text_elems=text_elems,
                signatures=signatures,
                has_title_font=has_title_font,
                has_author_font=has_author_font,
                line_start=line_start_flag,
            )
        )

    # 2.1 Détection titre / auteur_titre
    title_candidates_by_lid: Dict[str, List[Dict[str, Any]]] = {}
    author_title_line_id: Optional[str] = None

    for idx, info in enumerate(header_infos):
        lid = info["lid"]

        # Dès qu'on rencontre une ligne sans police de titre dans le header,
        # on considère que la zone de titre est terminée.
        if not info["has_title_font"]:
            break

        # Collecte des spans en police de titre
        for e in info["text_elems"]:
            if (
                e.get("element_type") is None
                and e.get("signature") in TITLE_SIGNATURES
            ):
                title_candidates_by_lid.setdefault(lid, []).append(e)

        # Heuristique pour trouver la ligne auteur_titre :
        #   - ligne en début de ligne
        #   - suivie d'une ligne avec police auteurs, sans police titre
        if author_title_line_id is None and info["line_start"] and idx + 1 < len(header_infos):
            nxt = header_infos[idx + 1]
            if not nxt["has_title_font"] and nxt["has_author_font"]:
                author_title_line_id = lid

    # Si on n'a pas trouvé l'auteur_titre avec l'heuristique,
    # on prend la première ligne avec police auteur.
    if author_title_line_id is None:
        for info in header_infos:
            if info["has_author_font"]:
                author_title_line_id = info["lid"]
                break

        # Cas dégradé : on étend les candidats de titre jusqu'à cette ligne
        if author_title_line_id is not None and not title_candidates_by_lid:
            for info in header_infos:
                lid = info["lid"]
                for e in info["text_elems"]:
                    if (
                        e.get("element_type") is None
                        and e.get("signature") in TITLE_SIGNATURES
                    ):
                        title_candidates_by_lid.setdefault(lid, []).append(e)
                if info["has_author_font"]:
                    break

    # Marquage des lignes de titre (abstract_title)
    for lid, elems in title_candidates_by_lid.items():
        if lid == author_title_line_id:
            continue
        for e in elems:
            if e.get("element_type") is None:
                e["element_type"] = "abstract_title"

    # Marquage de la ligne auteur_titre
    if author_title_line_id is not None:
        for e in lines[author_title_line_id]:
            if (
                e.get("type") == "text"
                and e.get("element_type") is None
                and e.get("signature") in TITLE_SIGNATURES
            ):
                e["element_type"] = "author_title"

    # 3) Auteurs + institutions (logique locale + globale multi-colonnes)
    if author_title_line_id is not None:
        idx_author_line = line_index_map[author_title_line_id]

        # 3.1 Ligne contenant un ';' : fin de la liste d'auteurs
        semicolon_line_idx: Optional[int] = None
        for j in range(idx_author_line, len(ordered_line_ids)):
            lid = ordered_line_ids[j]
            line_elems = lines[lid]

            # Si on tombe sur une section, on s'arrête
            if has_section_label(line_elems):
                break

            txt = concat_line_text(line_elems)
            if ";" in txt:
                semicolon_line_idx = j
                break

        if semicolon_line_idx is not None:
            # 3.2 Auteurs supplémentaires : entre auteur_titre et la ligne avec ';'
            for j in range(idx_author_line + 1, semicolon_line_idx + 1):
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

            # 3.3 Institutions
            #     - on détecte la première ligne d'institution dans la colonne du code
            #       (texte en AUTHOR_FONT, non typé, après la ligne avec ';')
            #     - puis on étend globalement sur le span jusqu'à la première section.
            institutions_start_idx = semicolon_line_idx + 1

            id_to_index = get_index_by_id(elements)
            first_inst_global_idx: Optional[int] = None

            for j in range(institutions_start_idx, len(ordered_line_ids)):
                lid = ordered_line_ids[j]
                line_elems = lines[lid]

                if has_section_label(line_elems):
                    break

                text_sorted = sorted(
                    [e for e in line_elems if e.get("type") == "text"],
                    key=lambda e: e.get("position", {}).get("x", 0.0),
                )
                if not text_sorted:
                    continue

                for te in text_sorted:
                    if (
                        te.get("element_type") is None
                        and te.get("signature") == AUTHOR_FONT
                    ):
                        first_inst_global_idx = id_to_index.get(te["id"])
                        break

                if first_inst_global_idx is not None:
                    break

            # Si on a trouvé un début d'institutions,
            # on étend jusqu'à la première section / disclosure / keywords / etc.
            if first_inst_global_idx is not None:
                BOUNDARY_TYPES = set(SECTION_TYPES) | {
                    "section_disclosure",
                    "section_keywords",
                    "section_supported_by",
                    "section_clinical_trial_registration_number",
                }

                inst_end_idx = span_end
                for idx in range(first_inst_global_idx, span_end + 1):
                    e = elements[idx]
                    if e.get("abstract_id") != abstract_id:
                        continue
                    if e.get("element_type") in BOUNDARY_TYPES:
                        inst_end_idx = idx - 1
                        break

                # Dans cette fenêtre, tout texte AUTHOR_FONT encore non typé
                # devient "institution" (toutes colonnes, multi-lignes).
                for idx in range(first_inst_global_idx, inst_end_idx + 1):
                    e = elements[idx]
                    if e.get("abstract_id") != abstract_id:
                        continue
                    if e.get("type") != "text":
                        continue
                    if e.get("element_type") is not None:
                        continue
                    if e.get("signature") != AUTHOR_FONT:
                        continue
                    e["element_type"] = "institution"

    # 4) Supported by / Clinical Trial Registration Number (étiquettes)
    for e in span_elems:
        if (
            e.get("type") == "text"
            and e.get("element_type") is None
            and e.get("signature") in IMAGE_TEXT_SIGNATURES
        ):
            txt = (e.get("text") or "").strip()
            low = txt.lower().replace("\u00a0", " ")
            if low.startswith("supported by:"):
                e["element_type"] = "section_supported_by"
            elif low.startswith("clinical trial registration number:"):
                e["element_type"] = "section_clinical_trial_registration_number"

    # 5) Gestion des sections (Background, Methods, Results, Conclusion, ... + Disclosure, Supported by, Trial Number)
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
                next_id = section_labels[i + 1].get("id")
                if next_id is None:
                    section_end_idx = span_end
                else:
                    nxt_idx = id_to_index.get(next_id, span_end + 1)
                    section_end_idx = min(nxt_idx - 1, span_end)
            else:
                section_end_idx = span_end

            # 5.1 Cas particuliers : Disclosure / Supported_by / Trial Number
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

            # 5.2 Sections "scientifiques" classiques : on distingue
            #      - le texte principal de section (AUTHOR_FONT)
            #      - le texte scientifique neutre (ABSTRACT_TEXT_SIGNATURES)
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

            # Texte scientifique "neutre" dans la même section
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

    # 6) Images / tables
    images: List[Dict[str, Any]] = []
    for e in span_elems:
        if e.get("type") == "image":
            if e.get("element_type") is None:
                e["element_type"] = "image"
            images.append(e)
        elif e.get("type") == "table":
            if e.get("element_type") is None:
                e["element_type"] = "table"

    # 7) image_text : texte en italique juste sous une image
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


# --- Entrée / sortie fichier --- #

def process_file(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input JSON not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or "elements" not in data:
        raise ValueError("Input JSON must be an object with 'elements'.")

    elements = data["elements"]
    if not isinstance(elements, list):
        raise ValueError("'elements' must be a list.")

    if not elements:
        data["elements"] = []
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return

    # Tri global des éléments pour garantir un ordre stable
    elements.sort(
        key=lambda e: element_global_key(e) if isinstance(e, dict) else (0, 0, 0.0, 0)
    )

    # Spans d'abstracts
    spans = compute_abstract_spans(elements)

    # Traitement de chaque abstract
    for abs_idx, (code_elem, span_start, span_end) in enumerate(spans, start=1):
        if not isinstance(code_elem, dict):
            continue
        abstract_id = f"abs_{abs_idx:04d}"
        process_single_abstract(elements, code_elem, span_start, span_end, abstract_id)

    data["elements"] = elements

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic typing pass 2.")
    parser.add_argument("-i", "--input", required=True, help="Input JSON (pass1).")
    parser.add_argument("-o", "--output", required=True, help="Output JSON (pass2).")
    args = parser.parse_args()

    process_file(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
