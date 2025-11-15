#!/usr/bin/env python3
# semantic_typing_pass_1.py
"""
Première passe de typage des éléments extraits (objectification simple).

Entrée :
    - JSON produit par neutral_extractor.py
Sortie :
    - même JSON, avec un champ "element_type" ajouté sur certains éléments texte.

Cette passe 1 fait uniquement :
    - Typage déterministe par signature + patterns simples :
        * header, session
        * code_abstract
        * sections (background & aims, materials & methods, results, conclusion)
        * section_disclosure
        * indice
        * symbol_text
        * footer

    - PAS de abstract_title / auteur / institution ici.
      On les traitera en passe 2 à partir du contexte (code_abstract, polices, lignes).
"""

import json
from pathlib import Path
import argparse
from typing import Optional

# --- Signatures "connues" -----------------------------------------------------

HEADER_SIGNATURE = "MyriadPro-SemiCn_8.5_4"
SESSION_SIGNATURE = "MyriadPro-Bold_12.0_20"

STIX_BOLD_8_5_20 = "STIX-Bold_8.5_20"
DISCLOSURE_SIGNATURE = "STIX-Italic_8.5_6"

# Signatures pour "indice" (petits indices, références, etc.)
INDICE_SIGNATURES = {
    "STIX-Italic_5.9_7",
    "STIX-Regular_5.9_5",
    "STIX-Regular_5.9_4",
    "STIX-Bold_5.9_20",
    "STIX-Bold_5.9_21",
    "STIX-Italic_5.9_6",
    "STIX-Regular_8.5_5",
    "SymbolMT_5.9_1",
}

# Texte symbolique / math
SYMBOL_TEXT_SIGNATURES = {
    "STIX-BoldItalic_8.5_22",
    "SymbolMT_8.5_0",
}

# Code abstract Times New Roman
TIMES_CODE_ABSTRACT_SIGNATURE = "TimesNewRomanPS-BoldMT_8.5_20"

# Footer Springer Nature
FOOTER_SIGNATURES = {
    "Springnew-Regular3_15.0_4",
    "Springnew-Regular2_15.0_4",
}


# --- Helpers ------------------------------------------------------------------


def normalize_section_label(text: str) -> str:
    """
    Normalise un texte de type 'Background and aims:', 'Results', etc.
    - strip espaces début/fin
    - enlève ':' final
    - lower()
    """
    t = text.strip()
    if t.endswith(":"):
        t = t[:-1]
    return t.strip().lower()


def looks_like_numeric_code(text: str) -> bool:
    """
    Détecte un code purement numérique type '1240', '03', '3'.
    """
    t = text.strip()
    if not t.isdigit():
        return False
    # on autorise 1 à 5 chiffres (adaptable)
    if not (1 <= len(t) <= 5):
        return False
    try:
        value = int(t)
    except ValueError:
        return False
    # borne large, on peut restreindre si besoin
    return 1 <= value <= 99999


def looks_like_alphanum_code(text: str) -> bool:
    """
    Détecte des codes de type 'LBA 03', 'LBA03', 'P1234', etc.

    Règle :
        - au plus 1 espace dans le texte original
        - text_clean = texte sans espaces
        - 2 <= len(text_clean) <= 8  (taille courte)
        - text_clean alphanumérique
        - contient au moins 1 lettre ET au moins 1 chiffre
    """
    t = text.strip()
    # trop d'espaces -> probablement pas un code
    if t.count(" ") > 1:
        return False

    text_clean = t.replace(" ", "")
    if not (2 <= len(text_clean) <= 8):
        return False

    if not text_clean.isalnum():
        return False

    has_letter = any(c.isalpha() for c in text_clean)
    has_digit = any(c.isdigit() for c in text_clean)

    return has_letter and has_digit


def looks_like_abstract_code(text: str) -> bool:
    """
    Un abstract_code est :
        - soit un code numérique (1240, 87, 0032)
        - soit un code alphanum court (LBA 03, P1234, etc.)
    """
    return looks_like_numeric_code(text) or looks_like_alphanum_code(text)


# --- Règle principale de typage ----------------------------------------------


def infer_element_type(elem: dict) -> Optional[str]:
    """
    Applique les règles de première passe à un élément.

    Renvoie :
        - une string (element_type)
        - ou None si aucune règle ne s'applique.
    """
    if elem.get("type") != "text":
        return None

    signature = elem.get("signature", "")
    text = elem.get("text", "")
    if not text:
        return None

    text_norm = text.strip()
    section_norm = normalize_section_label(text)

    # 1. Sections structurantes (STIX-Bold_8.5_20 + mots-clés)
    if signature == STIX_BOLD_8_5_20:
        # Background and aims
        if "background and aims" in section_norm:
            return "section_background_and_aims"
        # Materials and methods
        if "materials and methods" in section_norm:
            return "section_materials_and_methods"
        # Results
        if section_norm == "results" or "results" in section_norm:
            return "section_results"
        # Conclusion
        if section_norm == "conclusion" or "conclusions" in section_norm:
            return "section_conclusion"

    # 2. Disclosure (exact)
    if signature == DISCLOSURE_SIGNATURE and section_norm == "disclosure":
        return "section_disclosure"

    # 3. Code abstract (STIX ou Times), via looks_like_abstract_code
    if signature in {STIX_BOLD_8_5_20, TIMES_CODE_ABSTRACT_SIGNATURE}:
        if looks_like_abstract_code(text_norm):
            return "code_abstract"

    # 4. Session
    if signature == SESSION_SIGNATURE:
        return "session"

    # 5. Header (en-tête revue/page)
    if signature == HEADER_SIGNATURE:
        return "header"

    # 6. Footer
    if signature in FOOTER_SIGNATURES:
        return "footer"

    # 7. Texte symbolique / math
    if signature in SYMBOL_TEXT_SIGNATURES:
        return "symbol_text"

    # 8. Indice (notes, indices, symboles minuscules)
    if signature in INDICE_SIGNATURES:
        return "indice"

    # ⚠️ IMPORTANT :
    # On ne tente PAS de détecter abstract_title, auteurs ou institutions ici.
    # Ils seront déterminés en passe 2, à partir du contexte
    # (code_abstract, session, signatures, lignes, etc.).

    return None


# --- Traitement principal -----------------------------------------------------


def process_file(input_path: Path, output_path: Path) -> None:
    """
    Charge le JSON d'entrée, applique le typage de première passe,
    et écrit un nouveau JSON avec "element_type" ajouté.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier JSON d'entrée introuvable: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    elements = data.get("elements", [])
    typed_count = 0

    for elem in elements:
        element_type = infer_element_type(elem)
        if element_type is not None:
            elem["element_type"] = element_type
            typed_count += 1
        else:
            # On explicite le fait que le type n'est pas encore déterminé
            # (facilite les passes suivantes)
            elem.setdefault("element_type", None)

    # On garde le reste de la structure identique
    data["elements"] = elements

    # Métadonnée pour tracer la passe
    meta = data.get("metadata", {})
    meta["semantic_typing_pass_1"] = {
        "typed_elements": typed_count,
    }
    data["metadata"] = meta

    # Sauvegarde
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ Typage 1ère passe terminé.")
    print(f"  Fichier entrée : {input_path}")
    print(f"  Fichier sortie : {output_path}")
    print(f"  Éléments typés : {typed_count} / {len(elements)}")


# --- CLI ----------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Première passe de typage des éléments "
            "(objectification simple) à partir du JSON de neutral_extractor."
        )
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Fichier JSON d'entrée (sortie de neutral_extractor)."
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Fichier JSON de sortie avec element_type ajouté."
    )

    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    process_file(input_path, output_path)


if __name__ == "__main__":
    main()
