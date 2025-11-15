#!/usr/bin/env python3
"""
Module d'Extraction Neutre (Réutilisable)
Extrait les éléments PDF et les annote avec signatures typographiques pures
Sans interprétation sémantique

Version 1.5 : Détection Unicode subscripts/superscripts (₀₁₂ ⁰¹²) + ajustement tolérance
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter
import base64

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERREUR: PyMuPDF requis. Installez avec: pip install PyMuPDF")
    exit(1)

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NeutralExtractor:
    """Extracteur neutre réutilisable pour tous types de PDFs"""
    
    def __init__(self, merge_consecutive: bool = True, y_tolerance: float = 3.0):
        """
        Initialise l'extracteur
        
        Args:
            merge_consecutive: Si True, fusionne les éléments consécutifs de même signature
            y_tolerance: Tolérance en pixels pour considérer deux éléments sur la même ligne
        """
        self.merge_consecutive = merge_consecutive
        self.y_tolerance = y_tolerance
        
        logger.info(f"Extracteur neutre initialisé")
        logger.info(f"  Fusion consécutifs : {merge_consecutive}")
        logger.info(f"  Tolérance Y : {y_tolerance}px")
    
    def compute_signature(self, span: Dict[str, Any]) -> str:
        """
        Calcule la signature typographique pure d'un span
        
        Signature = Font_Size_Flags
        
        Args:
            span: Span PyMuPDF
            
        Returns:
            Signature sous forme "FontName_Size_Flags"
        """
        font = span.get("font", "Unknown")
        size = round(span.get("size", 0), 1)  # Arrondi à 1 décimale
        flags = span.get("flags", 0)
        
        return f"{font}_{size}_{flags}"
    
    def _extract_images(self, doc: fitz.Document, page_num: int, page: fitz.Page, 
                       output_base: str, image_counter: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Extrait les images d'une page et les sauvegarde dans un dossier
        
        Args:
            doc: Document PyMuPDF
            page_num: Numéro de page (1-indexed)
            page: Page PyMuPDF
            output_base: Chemin de base pour le nom de fichier de sortie (sans extension)
            image_counter: Compteur global d'images par page
            
        Returns:
            Liste d'éléments image avec références aux fichiers
        """
        images = []
        image_list = page.get_images(full=True)
        
        # Créer le dossier images
        images_dir = Path(output_base).parent / f"{Path(output_base).stem}_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                
                if not base_image:
                    continue
                
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Générer ID et nom de fichier
                if page_num not in image_counter:
                    image_counter[page_num] = 0
                
                image_id = f"p{page_num}_img{image_counter[page_num]}"
                image_filename = f"{image_id}.{image_ext}"
                image_path = images_dir / image_filename
                
                # Sauvegarder l'image
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                # Récupérer position sur la page
                img_rects = page.get_image_rects(xref)
                if img_rects:
                    rect = img_rects[0]  # Première occurrence
                    bbox = [rect.x0, rect.y0, rect.x1, rect.y1]
                else:
                    bbox = [0, 0, 0, 0]  # Position inconnue
                
                # Créer élément image
                image_elem = {
                    "type": "image",
                    "image_id": image_id,
                    "image_file": f"{Path(output_base).stem}_images/{image_filename}",
                    "page": page_num,
                    "position": {
                        "x": round(bbox[0], 2),
                        "y": round(bbox[1], 2),
                        "w": round(bbox[2] - bbox[0], 2),
                        "h": round(bbox[3] - bbox[1], 2)
                    },
                    "format": image_ext,
                    "size": {
                        "width": base_image["width"],
                        "height": base_image["height"]
                    },
                    "xref": xref
                }
                
                images.append(image_elem)
                image_counter[page_num] += 1
                
            except Exception as e:
                logger.warning(f"Erreur extraction image {img_index} page {page_num}: {e}")
        
        return images
    
    def _extract_tables(self, page: fitz.Page, page_num: int, table_counter: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Extrait les tables d'une page avec structure matricielle
        
        Args:
            page: Page PyMuPDF
            page_num: Numéro de page (1-indexed)
            table_counter: Compteur global de tables par page
            
        Returns:
            Liste d'éléments table avec structure matricielle
        """
        tables = []
        
        try:
            # Détection automatique des tables
            found_tables = page.find_tables()
            
            if page_num not in table_counter:
                table_counter[page_num] = 0
            
            for table in found_tables:
                try:
                    # ID unique
                    table_id = f"p{page_num}_tab{table_counter[page_num]}"
                    
                    # Position
                    bbox = table.bbox
                    
                    # Extraction des cellules
                    rows_count = table.row_count
                    cols_count = table.col_count
                    
                    # Structure matricielle
                    cells_matrix = []
                    for row_idx in range(rows_count):
                        row_cells = []
                        for col_idx in range(cols_count):
                            cell = table.cell(row_idx, col_idx)
                            cell_text = " ".join(cell) if isinstance(cell, list) else str(cell) if cell else ""
                            
                            # Récupérer bbox de la cellule si possible
                            try:
                                cell_bbox = table.cell_bbox(row_idx, col_idx)
                                cell_position = {
                                    "x": round(cell_bbox[0], 2),
                                    "y": round(cell_bbox[1], 2),
                                    "w": round(cell_bbox[2] - cell_bbox[0], 2),
                                    "h": round(cell_bbox[3] - cell_bbox[1], 2)
                                }
                            except:
                                cell_position = None
                            
                            cell_data = {
                                "text": cell_text.strip(),
                                "bbox": cell_position
                            }
                            row_cells.append(cell_data)
                        
                        cells_matrix.append(row_cells)
                    
                    # Créer élément table
                    table_elem = {
                        "type": "table",
                        "table_id": table_id,
                        "page": page_num,
                        "position": {
                            "x": round(bbox[0], 2),
                            "y": round(bbox[1], 2),
                            "w": round(bbox[2] - bbox[0], 2),
                            "h": round(bbox[3] - bbox[1], 2)
                        },
                        "rows": rows_count,
                        "cols": cols_count,
                        "cells": cells_matrix
                    }
                    
                    tables.append(table_elem)
                    table_counter[page_num] += 1
                    
                except Exception as e:
                    logger.warning(f"Erreur extraction table {table_counter[page_num]} page {page_num}: {e}")
        
        except Exception as e:
            logger.warning(f"Erreur détection tables page {page_num}: {e}")
        
        return tables
    
    def extract_from_pdf(self, pdf_path: str, start_page: int = 1, end_page: Optional[int] = None) -> Dict[str, Any]:
        """
        Extrait tous les éléments d'un PDF avec annotations de signature
        
        Args:
            pdf_path: Chemin du PDF
            start_page: Page de début (1-indexed)
            end_page: Page de fin (1-indexed, None = jusqu'à la fin)
            
        Returns:
            Dictionnaire avec éléments séquentiels et catalogue de signatures
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF non trouvé : {pdf_path}")
        
        logger.info(f"Ouverture du PDF : {pdf_path}")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        # Ajustement des limites
        start_idx = start_page - 1  # PyMuPDF est 0-indexed
        end_idx = (end_page if end_page else total_pages)
        
        logger.info(f"Extraction pages {start_page} à {end_idx} (sur {total_pages})")
        
        # Conteneurs
        raw_elements = []
        element_id = 0
        image_counter = {}
        table_counter = {}
        
        # Base du nom de fichier pour les images
        output_base = pdf_path.replace('.pdf', '')
        
        # Extraction
        for page_num in range(start_idx, end_idx):
            page = doc.load_page(page_num)
            page_num_1indexed = page_num + 1
            
            # === EXTRACTION TEXTE ===
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        
                        # Calcul signature
                        signature = self.compute_signature(span)
                        
                        # Extraction position
                        bbox = span["bbox"]
                        
                        element = {
                            "id": element_id,
                            "type": "text",
                            "page": page_num_1indexed,
                            "text": text,
                            "signature": signature,
                            "position": {
                                "x": round(bbox[0], 2),
                                "y": round(bbox[1], 2),
                                "w": round(bbox[2] - bbox[0], 2),
                                "h": round(bbox[3] - bbox[1], 2)
                            }
                        }
                        
                        raw_elements.append(element)
                        element_id += 1
            
            # === EXTRACTION IMAGES ===
            images = self._extract_images(doc, page_num_1indexed, page, output_base, image_counter)
            for img in images:
                img["id"] = element_id
                raw_elements.append(img)
                element_id += 1
            
            # === EXTRACTION TABLES ===
            tables = self._extract_tables(page, page_num_1indexed, table_counter)
            for tbl in tables:
                tbl["id"] = element_id
                raw_elements.append(tbl)
                element_id += 1
        
        doc.close()
        
        total_texts = sum(1 for e in raw_elements if e.get("type") == "text")
        total_images = sum(1 for e in raw_elements if e.get("type") == "image")
        total_tables = sum(1 for e in raw_elements if e.get("type") == "table")
        
        logger.info(f"✓ {total_texts} éléments texte extraits")
        logger.info(f"✓ {total_images} images extraites")
        logger.info(f"✓ {total_tables} tables extraites")
        
        # Fusion optionnelle (seulement pour les textes)
        if self.merge_consecutive:
            text_elements = [e for e in raw_elements if e.get("type") == "text"]
            non_text_elements = [e for e in raw_elements if e.get("type") != "text"]
            
            merged_texts = self._merge_consecutive_elements(text_elements)
            logger.info(f"✓ {len(merged_texts)} éléments texte après fusion")
            
            # Recombiner
            elements = merged_texts + non_text_elements
        else:
            elements = raw_elements
        
        # Tri par page puis position Y pour respecter l'ordre de lecture
        elements.sort(key=lambda e: (e["page"], e["position"]["y"]))
        
        # Ajout métadonnées de ligne
        elements = self._add_line_metadata(elements)
        logger.info(f"✓ Métadonnées de ligne ajoutées")
        
        # Génération du catalogue (seulement pour textes)
        text_elements_final = [e for e in elements if e.get("type") == "text"]
        catalog = self._build_signature_catalog(text_elements_final)
        
        # Structure finale
        result = {
            "metadata": {
                "source": pdf_path,
                "extraction_date": datetime.now().isoformat(),
                "extractor": "neutral_extractor",
                "version": "1.5",
                "total_elements": len(elements),
                "total_texts": len(text_elements_final),
                "total_images": total_images,
                "total_tables": total_tables,
                "pages_extracted": f"{start_page}-{end_idx}",
                "merge_consecutive": self.merge_consecutive,
                "line_metadata": True
            },
            "signature_catalog": catalog,
            "elements": elements
        }
        
        return result
    
    def _merge_consecutive_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fusionne les éléments consécutifs de même signature
        
        Critères de fusion :
        - Même signature
        - Même page
        - Proximité Y (même ligne approximative)
        - Continuité X (pas de grand saut)
        
        Args:
            elements: Liste d'éléments bruts
            
        Returns:
            Liste d'éléments fusionnés
        """
        if not elements:
            return elements
        
        merged = []
        current_group = [elements[0]]
        
        for i in range(1, len(elements)):
            prev = current_group[-1]
            curr = elements[i]
            
            should_merge = self._should_merge(prev, curr)
            
            if should_merge:
                current_group.append(curr)
            else:
                # Finaliser le groupe
                merged_elem = self._create_merged_element(current_group)
                merged.append(merged_elem)
                current_group = [curr]
        
        # Dernier groupe
        if current_group:
            merged_elem = self._create_merged_element(current_group)
            merged.append(merged_elem)
        
        return merged
    
    def _should_merge(self, elem1: Dict[str, Any], elem2: Dict[str, Any]) -> bool:
        """
        Détermine si deux éléments consécutifs doivent être fusionnés
        
        Args:
            elem1: Premier élément
            elem2: Élément suivant
            
        Returns:
            True si fusion recommandée
        """
        # Même signature obligatoire
        if elem1["signature"] != elem2["signature"]:
            return False
        
        # Même page obligatoire
        if elem1["page"] != elem2["page"]:
            return False
        
        # Proximité Y (même ligne approximative)
        y1 = elem1["position"]["y"]
        y2 = elem2["position"]["y"]
        if abs(y2 - y1) > self.y_tolerance:
            return False
        
        # Continuité X (pas de grand saut horizontal)
        x1_end = elem1["position"]["x"] + elem1["position"]["w"]
        x2_start = elem2["position"]["x"]
        gap = x2_start - x1_end
        
        # Tolérance : jusqu'à ~50px (espace entre mots/colonnes)
        if gap > 50:
            return False
        
        return True
    
    def _create_merged_element(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Crée un élément fusionné à partir d'un groupe
        
        Args:
            group: Liste d'éléments à fusionner
            
        Returns:
            Élément fusionné
        """
        if len(group) == 1:
            return group[0]
        
        first = group[0]
        last = group[-1]
        
        # Fusion des textes avec espaces
        merged_text = " ".join(elem["text"] for elem in group)
        
        # Position : du début du premier à la fin du dernier
        x_start = first["position"]["x"]
        y_start = first["position"]["y"]
        x_end = last["position"]["x"] + last["position"]["w"]
        y_end = max(elem["position"]["y"] + elem["position"]["h"] for elem in group)
        
        merged = {
            "id": first["id"],
            "page": first["page"],
            "text": merged_text,
            "signature": first["signature"],
            "position": {
                "x": round(x_start, 2),
                "y": round(y_start, 2),
                "w": round(x_end - x_start, 2),
                "h": round(y_end - y_start, 2)
            },
            "_merged_count": len(group)  # Info debug
        }
        
        return merged
    
    def _is_script_element(self, elem: Dict[str, Any]) -> tuple:
        """
        Détermine si un élément est un script (super ou subscript)
        
        Détecte les scripts par :
        1. Caractères Unicode dédiés (subscripts/superscripts natifs)
        2. Taille/hauteur réduites (scripts typographiques classiques)
        
        Args:
            elem: Élément à analyser
            
        Returns:
            (is_script: bool, script_type: str or None)
            script_type: 'super', 'sub', or None (déterminé plus tard par position Y)
        """
        text = elem.get("text", "")
        h = elem["position"]["h"]
        
        # Parse size from signature
        sig_parts = elem.get("signature", "_0_").split("_")
        size = float(sig_parts[1]) if len(sig_parts) > 1 else 0
        
        # Unicode subscripts (₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓ etc.)
        SUBSCRIPT_CHARS = (
            '\u2080\u2081\u2082\u2083\u2084'  # ₀₁₂₃₄
            '\u2085\u2086\u2087\u2088\u2089'  # ₅₆₇₈₉
            '\u208a\u208b\u208c\u208d\u208e'  # ₊₋₌₍₎
            '\u2090\u2091\u2092\u2093\u2094'  # ₐₑₒₓₔ
            '\u2095\u2096\u2097\u2098\u2099'  # ₕₖₗₘₙ
            '\u209a\u209b\u209c'              # ₚₛₜ
        )
        
        # Unicode superscripts (⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ)
        SUPERSCRIPT_CHARS = (
            '\u2070\u00b9\u00b2\u00b3'        # ⁰¹²³
            '\u2074\u2075\u2076\u2077'        # ⁴⁵⁶⁷
            '\u2078\u2079\u207a\u207b'        # ⁸⁹⁺⁻
            '\u207c\u207d\u207e\u207f'        # ⁼⁽⁾ⁿ
            '\u2071'                          # ⁱ
        )
        
        # Méthode 1 : Détection Unicode (prioritaire)
        if any(char in SUBSCRIPT_CHARS for char in text):
            return (True, 'sub')
        
        if any(char in SUPERSCRIPT_CHARS for char in text):
            return (True, 'super')
        
        # Méthode 2 : Détection par taille/hauteur (classique)
        if h < 9.0 or size < 7.0:
            # Type déterminé plus tard par position Y
            return (True, None)
        
        return (False, None)
    
    def _attach_scripts_to_lines(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rattache les scripts (superscripts et subscripts) à leur ligne de texte
        
        Gère trois types de scripts :
        - SUPERSCRIPTS typographiques : Y plus petit (~0.5px plus haut) - ex: références¹
        - SUBSCRIPTS typographiques : Y plus grand (~4px plus bas) - ex: HbA₁c
        - SCRIPTS Unicode : Caractères dédiés (₂, ², etc.) - détectés par contenu
        
        Cette méthode ajuste leur Y pour qu'ils soient groupés avec leur ligne de texte.
        
        Critères de détection :
        - Caractères Unicode subscript/superscript (₀₁₂ ou ⁰¹²)
        - Hauteur < 9px OU taille de police < 7.0
        
        Args:
            elements: Liste d'éléments
            
        Returns:
            Liste d'éléments avec Y ajusté pour les scripts
        """
        # Grouper par page
        by_page = {}
        for elem in elements:
            page = elem["page"]
            if page not in by_page:
                by_page[page] = []
            by_page[page].append(elem)
        
        result = []
        superscript_adjusted = 0
        subscript_adjusted = 0
        
        for page in sorted(by_page.keys()):
            page_elements = by_page[page]
            
            # Séparer scripts et texte normal (ignorer images et tables)
            small_elements = []  # Potentiels super/subscripts
            normal_text = []
            non_text = []
            
            for elem in page_elements:
                elem_type = elem.get("type", "text")
                
                # Ignorer images et tables
                if elem_type in ["image", "table"]:
                    non_text.append(elem)
                    continue
                
                # Détection script (taille/hauteur OU Unicode)
                is_script, script_type_hint = self._is_script_element(elem)
                
                if is_script:
                    # Marquer le type si déjà connu (Unicode)
                    if script_type_hint:
                        elem["_script_type_hint"] = script_type_hint
                    small_elements.append(elem)
                else:
                    normal_text.append(elem)
            
            # Rattacher chaque script à sa ligne de texte
            for small in small_elements:
                small_y = small["position"]["y"]
                small_x = small["position"]["x"]
                
                # Récupérer le hint de type si disponible (Unicode)
                type_hint = small.get("_script_type_hint")
                
                # Chercher le texte le plus proche
                closest = None
                min_distance = float('inf')
                script_type = type_hint  # Utiliser le hint si déjà connu
                
                for text_elem in normal_text:
                    text_y = text_elem["position"]["y"]
                    text_x = text_elem["position"]["x"]
                    
                    # Proximité X (pour éviter de rattacher à une ligne trop éloignée horizontalement)
                    x_dist = abs(text_x - small_x)
                    if x_dist > 100:
                        continue
                    
                    # Différence Y (signée)
                    y_diff = text_y - small_y
                    
                    # Si le type est déjà connu (Unicode), chercher le texte proche avec tolérance élargie
                    if type_hint:
                        distance = abs(y_diff)
                        # Tolérance élargie pour Unicode (±8px au lieu de ±2px)
                        # Car les caractères Unicode peuvent avoir Y très proche du texte normal
                        if distance < 8.0 and distance < min_distance:
                            min_distance = distance
                            closest = text_elem
                            # script_type déjà défini par type_hint
                    
                    # Sinon, détection classique par position Y
                    else:
                        # Cas 1 : SUPERSCRIPT (small_y < text_y, donc y_diff > 0)
                        # Le petit élément est au-DESSUS du texte
                        if 0.3 <= y_diff <= 2.0:
                            distance = y_diff
                            if distance < min_distance:
                                min_distance = distance
                                closest = text_elem
                                script_type = 'super'
                        
                        # Cas 2 : SUBSCRIPT (small_y > text_y, donc y_diff < 0)
                        # Le petit élément est en-DESSOUS du texte
                        elif -6.0 <= y_diff <= -2.0:
                            distance = abs(y_diff)
                            if distance < min_distance:
                                min_distance = distance
                                closest = text_elem
                                script_type = 'sub'
                
                # Ajuster Y si ligne trouvée
                if closest and script_type:
                    original_y = small["position"]["y"]
                    small["position"]["y"] = closest["position"]["y"]
                    small["_original_y"] = original_y
                    
                    if script_type == 'super':
                        small["_superscript_adjusted"] = True
                        superscript_adjusted += 1
                    else:  # 'sub'
                        small["_subscript_adjusted"] = True
                        subscript_adjusted += 1
            
            # Reconstituer la liste
            result.extend(normal_text)
            result.extend(small_elements)
            result.extend(non_text)
        
        if superscript_adjusted > 0:
            logger.info(f"✓ {superscript_adjusted} exposants (superscripts) rattachés à leur ligne")
        if subscript_adjusted > 0:
            logger.info(f"✓ {subscript_adjusted} indices (subscripts) rattachés à leur ligne")
        
        return result
    
    def _add_line_metadata(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ajoute les métadonnées de ligne à chaque élément
        
        Ordre de lecture : Colonne GAUCHE d'abord (haut→bas), puis Colonne DROITE (haut→bas)
        
        Métadonnées ajoutées :
        - line_id: Format "p{page}_L{num}" (ex: "p4_L0")
        - line_num: Compteur global par page (0, 1, 2...)
        - line_start: True si premier élément de la ligne
        - line_position: "left" (X < 305) ou "right" (X >= 305)
        
        Args:
            elements: Liste d'éléments
            
        Returns:
            Liste d'éléments avec métadonnées de ligne (ordre : gauche puis droite)
        """
        # ÉTAPE 0 : Rattacher les scripts (super et subscripts) à leur ligne AVANT le groupement
        elements = self._attach_scripts_to_lines(elements)
        
        LINE_Y_TOLERANCE = 0.3  # Tolérance stricte pour grouper sur même ligne
        X_THRESHOLD = 305       # Seuil gauche/droite
        
        # Grouper par page
        by_page = {}
        for elem in elements:
            page = elem["page"]
            if page not in by_page:
                by_page[page] = []
            by_page[page].append(elem)
        
        # Traiter chaque page
        result = []
        for page in sorted(by_page.keys()):
            page_elements = by_page[page]
            
            # ÉTAPE 1 : Séparer par colonne
            left_elements = [e for e in page_elements if e["position"]["x"] < X_THRESHOLD]
            right_elements = [e for e in page_elements if e["position"]["x"] >= X_THRESHOLD]
            
            line_counter = 0  # Compteur global pour la page
            
            # ÉTAPE 2 : Traiter COLONNE GAUCHE d'abord
            left_lines = self._group_by_line(left_elements, LINE_Y_TOLERANCE)
            for line in left_lines:
                # Trier éléments par X (gauche → droite)
                line.sort(key=lambda e: e["position"]["x"])
                
                for idx, elem in enumerate(line):
                    elem["line_id"] = f"p{page}_L{line_counter}"
                    elem["line_num"] = line_counter
                    elem["line_start"] = (idx == 0)
                    elem["line_position"] = "left"
                    
                    result.append(elem)
                
                line_counter += 1
            
            # ÉTAPE 3 : Traiter COLONNE DROITE ensuite (compteur continue)
            right_lines = self._group_by_line(right_elements, LINE_Y_TOLERANCE)
            for line in right_lines:
                # Trier éléments par X (gauche → droite)
                line.sort(key=lambda e: e["position"]["x"])
                
                for idx, elem in enumerate(line):
                    elem["line_id"] = f"p{page}_L{line_counter}"
                    elem["line_num"] = line_counter
                    elem["line_start"] = (idx == 0)
                    elem["line_position"] = "right"
                    
                    result.append(elem)
                
                line_counter += 1
        
        return result
    
    def _group_by_line(self, elements: List[Dict[str, Any]], y_tolerance: float) -> List[List[Dict[str, Any]]]:
        """
        Groupe les éléments par ligne (Y similaire)
        
        Args:
            elements: Liste d'éléments
            y_tolerance: Tolérance Y pour considérer même ligne
            
        Returns:
            Liste de lignes (chaque ligne = liste d'éléments), triée par Y
        """
        lines = []
        
        for elem in elements:
            y = elem["position"]["y"]
            
            # Trouver ligne existante
            found = False
            for line in lines:
                line_y = line[0]["position"]["y"]
                if abs(y - line_y) <= y_tolerance:
                    line.append(elem)
                    found = True
                    break
            
            if not found:
                lines.append([elem])
        
        # Trier lignes par Y (haut → bas)
        lines.sort(key=lambda line: line[0]["position"]["y"])
        
        return lines
    
    def _build_signature_catalog(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Construit le catalogue des signatures utilisées
        
        Args:
            elements: Liste d'éléments
            
        Returns:
            Dictionnaire signature → détails
        """
        # Comptage
        signature_counts = Counter(elem["signature"] for elem in elements)
        
        # Analyse de chaque signature
        catalog = {}
        
        for signature in signature_counts:
            # Parse signature
            parts = signature.split("_")
            font = parts[0] if len(parts) > 0 else "Unknown"
            size = float(parts[1]) if len(parts) > 1 else 0
            flags = int(parts[2]) if len(parts) > 2 else 0
            
            # Récupération exemples
            examples = [
                elem["text"][:50] for elem in elements 
                if elem["signature"] == signature
            ][:3]  # 3 premiers exemples
            
            catalog[signature] = {
                "font": font,
                "size": size,
                "flags": flags,
                "count": signature_counts[signature],
                "examples": examples
            }
        
        # Tri par fréquence décroissante
        catalog = dict(sorted(catalog.items(), key=lambda x: x[1]["count"], reverse=True))
        
        return catalog
    
    def save_to_json(self, data: Dict[str, Any], output_path: str):
        """
        Sauvegarde les données en JSON
        
        Args:
            data: Données à sauvegarder
            output_path: Chemin de sortie
        """
        # Création du dossier si nécessaire
        output_dir = Path(output_path).parent
        if output_dir != Path('.'):
            output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Données sauvegardées : {output_path}")
        
        # Rapport
        self._print_report(data)
    
    def _print_report(self, data: Dict[str, Any]):
        """Affiche un rapport d'extraction"""
        metadata = data["metadata"]
        catalog = data["signature_catalog"]
        elements = data["elements"]
        
        print("\n" + "="*70)
        print("RAPPORT D'EXTRACTION NEUTRE")
        print("="*70)
        
        print(f"\n📄 Source : {metadata['source']}")
        print(f"📊 Total éléments : {metadata['total_elements']}")
        print(f"   ├─ Textes : {metadata.get('total_texts', 0)}")
        print(f"   ├─ Images : {metadata.get('total_images', 0)}")
        print(f"   └─ Tables : {metadata.get('total_tables', 0)}")
        print(f"📑 Pages extraites : {metadata['pages_extracted']}")
        print(f"🔀 Fusion activée : {metadata['merge_consecutive']}")
        print(f"📏 Métadonnées ligne : {metadata.get('line_metadata', False)}")
        
        print(f"\n🔤 SIGNATURES TYPOGRAPHIQUES DÉTECTÉES : {len(catalog)}")
        print(f"\n   Top 10 par fréquence :")
        for i, (sig, details) in enumerate(list(catalog.items())[:10], 1):
            percentage = (details['count'] / metadata.get('total_texts', 1)) * 100
            print(f"   {i:2}. {sig}")
            print(f"       Count: {details['count']:4} ({percentage:5.1f}%) | Exemples: {details['examples'][0][:40]}...")
        
        # Stats de ligne
        if metadata.get('line_metadata'):
            left_count = sum(1 for e in elements if e.get('line_position') == 'left')
            right_count = sum(1 for e in elements if e.get('line_position') == 'right')
            line_starts = sum(1 for e in elements if e.get('line_start'))
            superscripts = sum(1 for e in elements if e.get('_superscript_adjusted'))
            subscripts = sum(1 for e in elements if e.get('_subscript_adjusted'))
            
            print(f"\n📍 STATISTIQUES DE LIGNE :")
            print(f"   Colonnes : Left={left_count} | Right={right_count}")
            print(f"   Débuts de ligne : {line_starts}")
            if superscripts > 0:
                print(f"   Exposants rattachés (superscripts) : {superscripts}")
            if subscripts > 0:
                print(f"   Indices rattachés (subscripts) : {subscripts}")
        
        # Stats images
        if metadata.get('total_images', 0) > 0:
            images_dir = Path(metadata['source']).parent / f"{Path(metadata['source']).stem}_images"
            print(f"\n🖼️  IMAGES :")
            print(f"   Dossier : {images_dir}")
            print(f"   Nombre : {metadata['total_images']}")
        
        # Stats tables
        if metadata.get('total_tables', 0) > 0:
            print(f"\n📋 TABLES :")
            print(f"   Nombre : {metadata['total_tables']}")
        
        print("\n" + "="*70)


def main():
    """Point d'entrée CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extracteur neutre - Extraction avec signatures typographiques pures"
    )
    parser.add_argument('-i', '--input', required=True, help='Fichier PDF d\'entrée')
    parser.add_argument('-o', '--output', default='neutral.json', help='Fichier JSON de sortie')
    parser.add_argument('-s', '--start-page', type=int, default=1, help='Page de début (défaut: 1)')
    parser.add_argument('-e', '--end-page', type=int, help='Page de fin (défaut: toutes)')
    parser.add_argument('--no-merge', action='store_true', help='Désactiver la fusion des consécutifs')
    parser.add_argument('--y-tolerance', type=float, default=3.0, help='Tolérance Y pour fusion (défaut: 3.0)')
    
    args = parser.parse_args()
    
    try:
        extractor = NeutralExtractor(
            merge_consecutive=not args.no_merge,
            y_tolerance=args.y_tolerance
        )
        
        data = extractor.extract_from_pdf(
            pdf_path=args.input,
            start_page=args.start_page,
            end_page=args.end_page
        )
        
        extractor.save_to_json(data, args.output)
        
        return 0
        
    except Exception as e:
        logger.error(f"Erreur : {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
