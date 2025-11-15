#!/usr/bin/env python3
# semantic_typing_pass_2.py
"""
Passe 2 : typage contextuel des éléments d'un abstract.

Entrée :
    - JSON produit par la passe 1 (semantic_typing_pass_1.py)
      contenant déjà :
        * code_abstract
        * section_* (labels)
        * header, footer, indice, symbol_text, etc.

Sortie :
    - même JSON, avec :
        * abstract_id ajouté aux éléments appartenant à un abstract
        * abstract_title
        * author_title
        * author
        * institution
        * section_*_text (background, methods, results, conclusion, disclosure)
        * abstract_text (texte résiduel dans les zones de sections)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Constantes de signatures / types connus ----------------------------------

TITLE_SIGNATURES = {
    "STIX-Bold_8.5_20",   # titre d'abstract typique
}

# Police "corps" principale (auteurs, sections, etc.)
AUTHOR_FONT = "STIX-Regular_8.5_4"

# Polices à considérer comme texte d'abstract (entre/à l'intérieur des sections)
ABSTRACT_TEXT_SIGNATURES = {
    "STIX-Regular_8.5_4",
    "STIX-BoldItalic_8.5_22",
    "SymbolMT_8.5_0",
}

# ⚠️ On ajoute ici section_disclosure pour générer section_disclosure_text
SECTION_TYPES = {
    "section_background_and_aims",
    "section_materials_and_methods",
    "section_results",
    "section_conclusion",
    "section_disclosure",
}

# -----------------------------------------------------------------------------


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
    return {
        e["id"]: idx
        for idx, e in enumerate(elements)
        if isinstance(e, dict) and "id" in e
    }


def concat_line_text(line_elems: List[Dict[str, Any]]) -> str:
    """
    Concatène le texte des éléments textuels d'une ligne.
    """
    parts: List[str] = []
    for e in line_elems:
        if e.get("type") == "text":
            parts.append(e.get("text", ""))
    return " ".join(parts).strip()


def has_section_label(line_elems: List[Dict[str, Any]]) -> bool:
    """
    True si la ligne contient un label de section (background, results, disclosure, etc.).
    """
    return any(e.get("element_type") in SECTION_TYPES for e in line_elems)


# --- Étape 1 : détermination des spans d'abstracts ---------------------------


def compute_abstract_spans(
    elements: List[Dict[str, Any]]
) -> List[Tuple[Dict[str, Any], int, int]]:
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


# --- Étape 2 : typage contextuel pour un abstract donné ----------------------


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
        - section_*_text (inclut section_disclosure_text)
        - abstract_text (résiduel dans les zones de sections)
    """

    # 1) Marquer tous les éléments du span avec abstract_id
    for i in range(span_start, span_end + 1):
        e = elements[i]
        if not isinstance(e, dict):
            continue
        e["abstract_id"] = abstract_id

    # Quelques raccourcis
    span_elems = [
        e for e in elements[span_start: span_end + 1]
        if isinstance(e, dict)
    ]

    # La colonne de l'abstract (left/right) est prise à partir du code_abstract
    code_column = code_elem.get("line_position")

    # On se limite à la même colonne que le code, et uniquement aux éléments après le code
    column_elems_after_code = []
    for e in span_elems:
        if e.get("line_position") != code_column:
            continue
        page = e.get("page", 0)
        code_page = code_elem.get("page", 0)
        if page > code_page or (page == code_page and e.get("id", 0) > code_elem.get("id", 0)):
            column_elems_after_code.append(e)

    if not column_elems_after_code:
        return

    # Regrouper par ligne
    lines = group_by_line(column_elems_after_code)
    if not lines:
        return

    ordered_line_ids = sort_line_ids(lines)
    line_index_map = {lid: idx for idx, lid in enumerate(ordered_line_ids)}

    # -------------------------------------------------------------------------
    # 2) Détection du abstract_title + author_title
    #    - Cas 1 : l'auteur_titre partage la même police que le titre
    #              et est suivi d'une ligne dans une autre police
    #    - Cas 2 : fallback sur l'ancienne heuristique (pivot AUTHOR_FONT)
    # -------------------------------------------------------------------------

    # 2.1. Construire la liste des lignes "en-tête" avant la première section
    header_line_ids: List[str] = []
    for lid in ordered_line_ids:
        line_elems = lines[lid]
        if has_section_label(line_elems):
            break
        header_line_ids.append(lid)

    if not header_line_ids:
        return

    # Infos pré-calculées par ligne
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

    title_candidates_by_lid: Dict[str, List[Dict[str, Any]]] = {}
    author_title_line_id: Optional[str] = None

    # 2.2. Heuristique principale : auteur_titre en même police que le titre
    for idx, info in enumerate(header_infos):
        lid = info["lid"]

        # On ne considère que le bloc de lignes avec police de titre, contigu à partir du haut
        if not info["has_title_font"]:
            break

        # Enregistrer les éléments titre de cette ligne comme candidats
        for e in info["text_elems"]:
            if (
                e.get("element_type") is None
                and e.get("signature") in TITLE_SIGNATURES
            ):
                title_candidates_by_lid.setdefault(lid, []).append(e)

        # Tester si cette ligne peut être l'auteur_titre :
        #  - elle démarre la ligne
        #  - la ligne suivante (si elle existe) n'est plus en police titre
        #  - et contient idéalement la police auteurs (AUTHOR_FONT)
        if author_title_line_id is None and info["line_start"] and idx + 1 < len(header_infos):
            next_info = header_infos[idx + 1]
            if not next_info["has_title_font"]:
                looks_like_authors = next_info["has_author_font"]
                if looks_like_authors:
                    author_title_line_id = lid

    # 2.3. Fallback : première ligne contenant AUTHOR_FONT comme pivot
    if author_title_line_id is None:
        for info in header_infos:
            if info["has_author_font"]:
                author_title_line_id = info["lid"]
                break

        # Si pivot trouvé mais pas de candidats titre, on les reconstitue
        if author_title_line_id is not None and not title_candidates_by_lid:
            for info in header_infos:
                lid = info["lid"]
                if has_section_label(info["line_elems"]):
                    break
                for e in info["text_elems"]:
                    if (
                        e.get("element_type") is None
                        and e.get("signature") in TITLE_SIGNATURES
                    ):
                        title_candidates_by_lid.setdefault(lid, []).append(e)
                if info["has_author_font"]:
                    break

    # 2.4. Application des types :
    #      - toutes les lignes candidates titre, sauf author_title_line_id → abstract_title
    #      - la ligne author_title_line_id → author_title
    for lid, elems in title_candidates_by_lid.items():
        if lid == author_title_line_id:
            continue
        for e in elems:
            if e.get("element_type") is None:
                e["element_type"] = "abstract_title"

    if author_title_line_id is not None:
        author_line_elems = lines[author_title_line_id]
        for e in author_line_elems:
            if (
                e.get("type") == "text"
                and e.get("element_type") is None
                and e.get("signature") in TITLE_SIGNATURES
            ):
                e["element_type"] = "author_title"

    # -------------------------------------------------------------------------
    # 3) Auteurs supplémentaires + Institutions
    # -------------------------------------------------------------------------

    if author_title_line_id is not None:
        idx_author_line = line_index_map[author_title_line_id]

        # 3.1. Chercher la première ligne (à partir de author_title) contenant un ';'
        semicolon_line_idx: Optional[int] = None

        for j in range(idx_author_line, len(ordered_line_ids)):
            lid = ordered_line_ids[j]
            line_elems = lines[lid]

            if has_section_label(line_elems):
                break

            line_text = concat_line_text(line_elems)
            if ";" in line_text:
                semicolon_line_idx = j
                break

        # 3.2. Lignes auteurs supplémentaires
        if semicolon_line_idx is not None:
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

            # 3.3. Institutions : lignes suivant celle avec ';'
            institutions_start_idx = semicolon_line_idx + 1

            for j in range(institutions_start_idx, len(ordered_line_ids)):
                lid = ordered_line_ids[j]
                line_elems = lines[lid]

                if has_section_label(line_elems):
                    break

                text_elems_sorted = sorted(
                    [e for e in line_elems if e.get("type") == "text"],
                    key=lambda e: e.get("position", {}).get("x", 0.0)
                )

                if not text_elems_sorted:
                    break

                first_text = text_elems_sorted[0]

                if first_text.get("element_type") == "indice":
                    for e in text_elems_sorted:
                        if e.get("element_type") is None and e.get("type") == "text":
                            e["element_type"] = "institution"
                    continue
                else:
                    break
        # sinon : pas d'institutions détectées, on laisse tel quel

    # -------------------------------------------------------------------------
    # 4) Texte des sections : section_*_text + abstract_text
    #    Inclut section_disclosure_text pour la section_disclosure
    # -------------------------------------------------------------------------

    section_labels = [
        e for e in span_elems
        if e.get("element_type") in SECTION_TYPES
    ]
    section_labels.sort(key=lambda e: e.get("id", 0))

    if section_labels:
        id_to_index = get_index_by_id(elements)

        for i, label in enumerate(section_labels):
            label_type = label.get("element_type")
            label_idx = id_to_index.get(label["id"])
            if label_idx is None:
                continue

            if i < len(section_labels) - 1:
                next_label = section_labels[i + 1]
                next_idx = id_to_index.get(next_label["id"], span_end + 1)
                section_end_idx = min(next_idx - 1, span_end)
            else:
                # ⚠️ Dernière section (souvent disclosure) :
                #     va jusqu'à la fin de l'abstract (span_end),
                #     donc "jusqu'au prochain code/session".
                section_end_idx = span_end

            # 4.1 Texte de section en AUTHOR_FONT -> section_*_text
            section_text_elems: List[Dict[str, Any]] = []
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
                if e.get("signature") != AUTHOR_FONT:
                    continue
                section_text_elems.append(e)

            for e in section_text_elems:
                if e.get("element_type") is None:
                    # ex : section_background_and_aims -> section_background_and_aims_text
                    e["element_type"] = f"{label_type}_text"

            # 4.2 Texte résiduel (corps/italique/symbole) -> abstract_text
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

    # S'il n'y a aucune section, on pourrait typer tout le corps en abstract_text
    # mais ce comportement n'est pas activé ici pour rester minimaliste.


# --- Pipeline global sur le fichier ------------------------------------------


def process_file(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier JSON d'entrée introuvable : {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Racine = dict, éléments dans "elements"
    if isinstance(data, dict):
        elements = data.get("elements", [])
        if not isinstance(elements, list):
            raise ValueError("Le champ 'elements' du JSON doit être une liste.")
    else:
        elements = data

    if not elements:
        raise ValueError("Aucun élément trouvé dans le JSON d'entrée.")

    # On s'assure que les éléments sont triés par id
    elements.sort(
        key=lambda e: e.get("id", 0) if isinstance(e, dict) else 0
    )

    # 1) calcul des spans d'abstracts
    spans = compute_abstract_spans(elements)

    # 2) traiter chaque abstract
    for abs_idx, (code_elem, span_start, span_end) in enumerate(spans, start=1):
        if not isinstance(code_elem, dict):
            continue
        abstract_id = f"abs_{abs_idx:04d}"
        process_single_abstract(elements, code_elem, span_start, span_end, abstract_id)

    # 3) sauvegarde
    if isinstance(data, dict):
        data["elements"] = elements
        to_dump = data
    else:
        to_dump = elements

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(to_dump, f, ensure_ascii=False, indent=2)


# --- CLI ---------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Passe 2 : typage contextuel des éléments d'un abstract."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Fichier JSON en entrée (sortie de semantic_typing_pass_1.py).",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Fichier JSON de sortie avec typage contextuel enrichi.",
    )

    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    process_file(input_path, output_path)


if __name__ == "__main__":
    main()
