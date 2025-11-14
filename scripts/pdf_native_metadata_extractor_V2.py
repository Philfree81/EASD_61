#!/usr/bin/env python3
"""
Extracteur PDF avec métadonnées exploitables pour analyse de structure
Optimisé pour documents médicaux avec structure répétitive
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from dotenv import load_dotenv

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedMetadataExtractor:
    """Extracteur PDF avec métadonnées exploitables pour analyse structurelle."""
    
    def __init__(self):
        """Initialise l'extracteur."""
        # Chargement de la configuration
        script_dir = Path(__file__).parent
        env_path = script_dir / '.env'
        if not env_path.exists():
            env_path = Path('.env')
        
        load_dotenv(env_path)
        
        self.pdf_input_path = os.getenv('INPUT_ORIGINAL_PDF', 'original.pdf')
        self.json_output_path = os.getenv('OUTPUT_EXTRACT_RAW', '_datastructured.json')
        
        # Validation des bibliothèques
        if not PYMUPDF_AVAILABLE and not PDFPLUMBER_AVAILABLE:
            raise ImportError("Au moins une bibliothèque PDF doit être installée : pip install PyMuPDF ou pip install pdfplumber")
        
        logger.info(f"Configuration chargée - PDF: {self.pdf_input_path}, JSON: {self.json_output_path}")
        logger.info(f"Bibliothèques disponibles - PyMuPDF: {PYMUPDF_AVAILABLE}, pdfplumber: {PDFPLUMBER_AVAILABLE}")
        
        # Création des dossiers de sortie si nécessaire
        output_dir = Path(self.json_output_path).parent
        if output_dir != Path('.'):
            output_dir.mkdir(parents=True, exist_ok=True)
    
    def _should_continue_line(self, current_line: List[Dict], next_char: Dict) -> bool:
        if not current_line:
            return False
        
        line_text = "".join(char["text"] for char in current_line).strip()
        last_char = current_line[-1]

         # Debug
        print(f"Test fusion: '{line_text}' + '{next_char['text']}'")
        print(f"  Point final: {line_text.endswith('.')}")
        print(f"  Police: {last_char.get('fontname', '')} == {next_char.get('fontname', '')}")
    
        
        return (
            not line_text.endswith('.') and                                    # Pas de fin logique
            last_char.get("fontname", "") == next_char.get("fontname", "") and # Même police
            abs(last_char.get("size", 0) - next_char.get("size", 0)) <= 0.5 and # Même taille
            not re.match(r'^[¹²³⁴⁵⁶⁷⁸⁹⁰\d]', next_char["text"]) and         # Pas d'indice
            abs(next_char["top"] - last_char["top"]) <= 40                     # Garde-fou 40px
        )

    def _are_scientific_compatible_fonts(self, prev_elem: Dict, curr_elem: Dict) -> bool:
        """Tolérance pour variations typographiques scientifiques"""
        
        prev_font = prev_elem.get("Font", "")
        curr_font = curr_elem.get("Font", "")
        
        # Même famille de base (AdvOT, Times, Arial...)
        prev_base = re.sub(r'[+\d]+|\.I|\.B|b\w+', '', prev_font)
        curr_base = re.sub(r'[+\d]+|\.I|\.B|b\w+', '', curr_font)
        
        return prev_base == curr_base

    def _should_merge_elements(self, prev_elem: Dict, curr_elem: Dict) -> bool:
        """Détermine si deux éléments doivent être fusionnés"""
        
        # Même page obligatoire
        if prev_elem.get("Page") != curr_elem.get("Page"):
            return False
        
        # Pas de fin logique sur l'élément précédent
        if prev_elem.get("Text", "").strip().endswith('.'):
            return False
        
        # Vérification de compatibilité des polices scientifiques
        if not self._are_scientific_compatible_fonts(prev_elem, curr_elem):
            return False
        
        # Extraction des polices pour la vérification suivante
        prev_font = prev_elem.get("Font", "")
        curr_font = curr_elem.get("Font", "")
        
        # Vérification de compatibilité des polices standard
        if not self._are_compatible_fonts(prev_font, curr_font):
            return False
        
        # Même taille (tolérance 0.5)
        if abs(prev_elem.get("FontSize", 0) - curr_elem.get("FontSize", 0)) > 0.5:
            return False
        
        # Pas d'indice numérique en début du suivant
        curr_text = curr_elem.get("Text", "").strip()
        if re.match(r'^[¹²³⁴⁵⁶⁷⁸⁹⁰\d]', curr_text):
            return False
        
        # Distance Y raisonnable (40px)
        prev_y = prev_elem.get("Position", {}).get("y", 0)
        curr_y = curr_elem.get("Position", {}).get("y", 0)
        if abs(curr_y - prev_y) > 40:
            return False
        
        return True
        
    def _are_compatible_fonts(self, font1: str, font2: str) -> bool:
        """Vérifie si deux polices sont compatibles (même base avec variantes autorisées)"""
        
        # Identiques = OK
        if font1 == font2:
            return True
        
        # Retire les suffixes +XX pour comparer la base
        base1 = re.sub(r'\+\d+$', '', font1)
        base2 = re.sub(r'\+\d+$', '', font2)
        
        return base1 == base2

    def _create_merged_element(self, element_group: List[Dict]) -> Dict:
        """Crée un élément fusionné à partir d'un groupe d'éléments"""
        if not element_group:
            return {}
        
        first_elem = element_group[0]
        
        # Fusionne les textes
        merged_text = " ".join(elem.get("Text", "").strip() for elem in element_group)
        
        # Calcule les nouvelles bounds
        min_x = min(elem.get("Position", {}).get("x", 0) for elem in element_group)
        min_y = min(elem.get("Position", {}).get("y", 0) for elem in element_group)
        max_x = max(elem.get("Position", {}).get("x", 0) + elem.get("Position", {}).get("width", 0) for elem in element_group)
        max_y = max(elem.get("Position", {}).get("y", 0) + elem.get("Position", {}).get("height", 0) for elem in element_group)
        
        # Crée l'élément fusionné basé sur le premier
        merged_element = first_elem.copy()
        merged_element.update({
            "Text": merged_text,
            "TextSize": len(merged_text),
            "Position": {
                "x": min_x,
                "y": min_y,
                "width": max_x - min_x,
                "height": max_y - min_y
            },
            "Bounds": [min_x, min_y, max_x, max_y],
            "_merged_from": len(element_group)  # Pour debug
        })
        
        return merged_element

    def _merge_consecutive_elements(self, elements: List[Dict]) -> List[Dict]:
        """Fusionne les éléments consécutifs selon nos critères"""
        if not elements:
            return elements
        
        merged = []
        current_group = [elements[0]]
        
        for i in range(1, len(elements)):
            prev_elem = current_group[-1]
            curr_elem = elements[i]
            
            if self._should_merge_elements(prev_elem, curr_elem):
                current_group.append(curr_elem)
            else:
                # Finalise le groupe
                if len(current_group) > 1:
                    merged_elem = self._create_merged_element(current_group)
                    merged.append(merged_elem)
                else:
                    merged.append(current_group[0])
                
                current_group = [curr_elem]
        
        # Traite le dernier groupe
        if current_group:
            if len(current_group) > 1:
                merged_elem = self._create_merged_element(current_group)
                merged.append(merged_elem)
            else:
                merged.append(current_group[0])
        
        return merged

    def extract_pdf_with_metadata(self) -> Dict[str, Any]:
        """Extrait le PDF avec métadonnées exploitables."""
        if not Path(self.pdf_input_path).exists():
            raise FileNotFoundError(f"Le fichier PDF n'existe pas : {self.pdf_input_path}")
        
        logger.info(f"Début de l'extraction avec métadonnées : {self.pdf_input_path}")
        
        # Structure de base
        extracted_data = {
            "elements": [],
            "pages": [],
            "metadata_analysis": {}
        }
        
        if PYMUPDF_AVAILABLE:
            extracted_data = self._extract_with_pymupdf(extracted_data)
        elif PDFPLUMBER_AVAILABLE:
            extracted_data = self._extract_with_pdfplumber(extracted_data)
        
        # Analyse des métadonnées extraites
        extracted_data["metadata_analysis"] = self._analyze_metadata(extracted_data["elements"])
        
        # Ajout des infos d'extraction
        extracted_data["_extraction_info"] = {
            "source_pdf": self.pdf_input_path,
            "extraction_date": datetime.now().isoformat(),
            "extractor_version": "enhanced-metadata-v1.0",
            "total_elements": len(extracted_data["elements"])
        }
        
        logger.info("Extraction avec métadonnées terminée avec succès")

        # Post-traitement des session_code
        
        
        return extracted_data
    
    def _extract_with_pymupdf(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extraction avec PyMuPDF et métadonnées enrichies."""
        logger.info("Utilisation de PyMuPDF pour l'extraction")
        
        doc = fitz.open(self.pdf_input_path)
        element_id = 0
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_data = {
                "pageNumber": page_num + 1,
                "width": page.rect.width,
                "height": page.rect.height
            }
            
            # Extraction du texte avec métadonnées complètes
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" in block:  # Bloc de texte
                    for line in block["lines"]:
                        line_elements = self._process_line_with_metadata(line, page_num + 1, element_id)
                        extracted_data["elements"].extend(line_elements)
                        element_id += len(line_elements)
            
            # Extraction des tableaux avec métadonnées
            tables = self._extract_tables_with_metadata(page, page_num + 1)
            for table_data in tables:
                table_element = {
                    "ElementID": element_id,
                    "Type": "table",
                    "Page": page_num + 1,
                    "Bounds": table_data["bounds"],
                    "Table": table_data["table"],
                    "CellCount": table_data.get("cell_count", 0),
                    "RowCount": table_data.get("row_count", 0),
                    "ColumnCount": table_data.get("column_count", 0)
                }
                extracted_data["elements"].append(table_element)
                element_id += 1
            # Après les boucles de blocs
            #extracted_data["elements"] = self._merge_consecutive_elements(extracted_data["elements"])
            extracted_data["pages"].append(page_data)
        
        doc.close()
        return extracted_data
    
    def _process_line_with_metadata(self, line: Dict, page_num: int, start_element_id: int) -> List[Dict[str, Any]]:
        """Traite une ligne avec détection des exposants et métadonnées complètes."""
        line_elements = []
        element_id = start_element_id
        
        if "spans" not in line:
            return line_elements
        
        spans = line["spans"]
        
        # Reconstruction intelligente de la ligne avec détection d'exposants
        processed_spans = self._group_and_process_spans(spans)
        
        for span_group in processed_spans:
            text = span_group["text"]
            bounds = span_group["bounds"]
            font_info = span_group["font_info"]
            
            if text.strip():
                # Classification automatique du type d'élément
                element_type = self._classify_element_type(text, font_info["size"], bounds, font_info["name"])
                
                element = {
                    "ElementID": element_id,
                    "Type": element_type,
                    "Text": text,
                    "Page": page_num,
                    "Bounds": bounds,
                    "Font": font_info["name"],
                    "FontSize": font_info["size"],
                    "FontFlags": font_info.get("flags", 0),  # Bold, Italic, etc.
                    "TextSize": len(text),
                    "Position": {
                        "x": bounds[0],
                        "y": bounds[1],
                        "width": bounds[2] - bounds[0],
                        "height": bounds[3] - bounds[1]
                    },
                    "IsSuper": span_group.get("is_superscript", False)
                }
                
                line_elements.append(element)
                element_id += 1
        
        return line_elements
    
    def _group_and_process_spans(self, spans: List[Dict]) -> List[Dict[str, Any]]:
        """Groupe les spans et traite les exposants."""
        if not spans:
            return []
        
        # Tri par position horizontale
        sorted_spans = sorted(spans, key=lambda s: s["bbox"][0])
        
        processed = []
        i = 0
        
        while i < len(sorted_spans):
            current_span = sorted_spans[i]
            
            # Vérification si c'est un exposant
            is_superscript = self._is_superscript_span(current_span, sorted_spans)
            
            if is_superscript:
                # Regrouper les exposants consécutifs
                superscript_text = ""
                superscript_bounds = list(current_span["bbox"])
                
                while i < len(sorted_spans) and self._is_superscript_span(sorted_spans[i], sorted_spans):
                    span = sorted_spans[i]
                    superscript_text += span["text"]
                    # Étendre les bounds
                    superscript_bounds[2] = max(superscript_bounds[2], span["bbox"][2])
                    i += 1
                
                # Convertir en exposant Unicode
                superscript_text = self._convert_to_unicode_superscript(superscript_text)
                
                processed.append({
                    "text": superscript_text,
                    "bounds": superscript_bounds,
                    "font_info": {
                        "name": current_span.get("font", ""),
                        "size": current_span.get("size", 0),
                        "flags": current_span.get("flags", 0)
                    },
                    "is_superscript": True
                })
            else:
                # Span normal
                processed.append({
                    "text": current_span["text"],
                    "bounds": list(current_span["bbox"]),
                    "font_info": {
                        "name": current_span.get("font", ""),
                        "size": current_span.get("size", 0),
                        "flags": current_span.get("flags", 0)
                    },
                    "is_superscript": False
                })
                i += 1
        
        return processed




    def _classify_element_type(self, text: str, font_size: float, bounds: List[float], font: str) -> str:
        text_clean = text.strip()
        
        # Session codes
        session_patterns = [
            r"^[A-Z]{2,3}-\d{3,4}$",
            r"^[A-Z]{2,3}-\d{3,4}-[A-Z0-9]{2}$", 
            r"^TOP-\d{3}$"
        ]
    def _classify_element_type(self, text: str, font_size: float, bounds: List[float], font: str) -> str:
        text_clean = text.strip()
        
        # Session codes
        session_patterns = [
            r"^[A-Z]{2,3}-\d{3,4}$",
            r"^[A-Z]{2,3}-\d{3,4}-[A-Z0-9]{2}$", 
            r"^TOP-\d{3}$"
        ]
        
        for pattern in session_patterns:
            if re.match(pattern, text_clean):
                # NOUVEAU: Validation par police
                if ".B" in font:
                    return "session_code"  # Vrai abstract (police gras)
                else:
                    return "reference"     # Citation (police normale)
        
        # Reste de la logique existante...
        
        
        # Font gras : distinction par contenu
        if font.endswith('.B'):
            if re.match(r'^(Background and aims?|Methods?|Results?|Conclusions?):?$', text_clean, re.IGNORECASE):
                return "section_header"
            else:
                return "title"
        
        # Auteurs (police droite + pattern noms)
        if (re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)+', text_clean) and
            not font.endswith('.I') and not font.endswith('.B')):
            return "author"
        
        # Institutions (police italique)
        if font.endswith('.I'):
            return "institution"
        
        # Défaut neutre pour le parser
        return "reference"

    def _is_superscript_span(self, span: Dict, all_spans: List[Dict]) -> bool:
        """Détecte si un span est un exposant."""
        span_size = span.get("size", 0)
        span_y = span["bbox"][1]
        span_text = span["text"].strip()
        
        if len(span_text) > 3 or not re.match(r'^[\d,\-\s]+$', span_text):
            return False
        
        # Comparaison avec les autres spans de la ligne
        for other_span in all_spans:
            other_size = other_span.get("size", 0)
            other_y = other_span["bbox"][1]
            
            if (span_size < other_size * 0.8 and 
                span_y < other_y - 2 and 
                len(other_span["text"].strip()) > len(span_text)):
                return True
        
        return False
    
    def _convert_to_unicode_superscript(self, text: str) -> str:
        """Convertit en exposants Unicode."""
        superscript_map = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
            ',': '‚', '-': '⁻', ' ': ''
        }
        
        return ''.join(superscript_map.get(char, char) for char in text)
    
    def _extract_tables_with_metadata(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extrait les tableaux avec métadonnées détaillées."""
        tables = []
        
        try:
            if hasattr(page, 'find_tables'):
                detected_tables = page.find_tables()
                for table in detected_tables:
                    table_data = table.extract()
                    if table_data:
                        bounds = table.bbox
                        row_count = len(table_data)
                        column_count = max(len(row) for row in table_data) if table_data else 0
                        cell_count = sum(len(row) for row in table_data)
                        
                        tables.append({
                            "bounds": [bounds[0], bounds[1], bounds[2], bounds[3]],
                            "table": self._format_table_data(table_data),
                            "row_count": row_count,
                            "column_count": column_count,
                            "cell_count": cell_count
                        })
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction de tableaux : {e}")
        
        return tables
    
    def _format_table_data(self, raw_table: List[List[str]]) -> List[List[Dict[str, Any]]]:
        """Formate les données de tableau."""
        formatted_table = []
        
        for row in raw_table:
            formatted_row = []
            for cell in row:
                cell_data = {
                    "content": [{"text": str(cell) if cell is not None else ""}]
                }
                formatted_row.append(cell_data)
            formatted_table.append(formatted_row)
        
        return formatted_table
    
    def _extract_with_pdfplumber(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extraction avec pdfplumber (version simplifiée)."""
        logger.info("Utilisation de pdfplumber pour l'extraction")
        
        element_id = 0
        
        with pdfplumber.open(self.pdf_input_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_data = {
                    "pageNumber": page_num + 1,
                    "width": float(page.width),
                    "height": float(page.height)
                }
                
                # Extraction des caractères avec métadonnées
                chars = page.chars
                if chars:
                    lines = self._group_chars_by_lines(chars)
                    
                    for line_chars in lines:
                        line_text = self._reconstruct_line_with_superscripts(line_chars)
                        
                        if line_text.strip():
                            # Calcul des métadonnées de ligne
                            min_x = min(char["x0"] for char in line_chars)
                            min_y = min(char["top"] for char in line_chars)
                            max_x = max(char["x1"] for char in line_chars)
                            max_y = max(char["bottom"] for char in line_chars)
                            
                            # Police et taille dominante
                            font_sizes = [char.get("size", 0) for char in line_chars]
                            dominant_font = max(set(char.get("fontname", "") for char in line_chars), 
                                              key=lambda x: sum(1 for char in line_chars if char.get("fontname", "") == x))
                            dominant_size = max(font_sizes) if font_sizes else 0
                            
                            # Classification
                            element_type = self._classify_element_type(line_text, dominant_size, [min_x, min_y, max_x, max_y])
                            
                            element = {
                                "ElementID": element_id,
                                "Type": element_type,
                                "Text": line_text,
                                "Page": page_num + 1,
                                "Bounds": [float(min_x), float(min_y), float(max_x), float(max_y)],
                                "Font": dominant_font,
                                "FontSize": float(dominant_size),
                                "TextSize": len(line_text),
                                "Position": {
                                    "x": float(min_x),
                                    "y": float(min_y),
                                    "width": float(max_x - min_x),
                                    "height": float(max_y - min_y)
                                }
                            }
                            
                            extracted_data["elements"].append(element)
                            element_id += 1
                
                extracted_data["pages"].append(page_data)
        
        return extracted_data
    
    def _group_chars_by_lines(self, chars: List[Dict]) -> List[List[Dict]]:
        """Groupe les caractères par lignes."""
        if not chars:
            return []
        
        sorted_chars = sorted(chars, key=lambda c: (c["top"], c["x0"]))
        lines = []
        current_line = [sorted_chars[0]]
        current_y = sorted_chars[0]["top"]
        tolerance = 3
        
        for char in sorted_chars[1:]:
            # Condition 1 : Tolérance Y normale
            if abs(char["top"] - current_y) <= tolerance:
                current_line.append(char)
            
            # Condition 2 : Fusion intelligente si conditions remplies
            elif self._should_continue_line(current_line, char):
                current_line.append(char)
                current_y = char["top"]  # Met à jour Y de référence
            
            # Sinon : nouvelle ligne
            else:
                lines.append(current_line)
                current_line = [char]
                current_y = char["top"]
                
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _reconstruct_line_with_superscripts(self, line_chars: List[Dict]) -> str:
        """Reconstruit une ligne avec gestion des exposants."""
        if not line_chars:
            return ""
        
        sorted_chars = sorted(line_chars, key=lambda c: c["x0"])
        line_text = ""
        base_size = max(char.get("size", 0) for char in sorted_chars)
        base_y = max(char.get("bottom", 0) for char in sorted_chars)
        
        i = 0
        while i < len(sorted_chars):
            char = sorted_chars[i]
            char_text = char["text"]
            char_size = char.get("size", 0)
            char_y = char.get("bottom", 0)
            
            is_superscript = (
                char_size < base_size * 0.8 and
                char_y < base_y - 2 and
                re.match(r'^[\d,\-\s]$', char_text)
            )
            
            if is_superscript:
                superscript_text = ""
                while (i < len(sorted_chars) and 
                       sorted_chars[i].get("size", 0) < base_size * 0.8 and
                       sorted_chars[i].get("bottom", 0) < base_y - 2):
                    superscript_text += sorted_chars[i]["text"]
                    i += 1
                
                line_text += self._convert_to_unicode_superscript(superscript_text)
            else:
                line_text += char_text
                i += 1
        
        return line_text
    
    def _analyze_metadata(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse les métadonnées extraites pour fournir des insights."""
        if not elements:
            return {}
        
        # Collecte des statistiques
        font_sizes = [elem.get("FontSize", 0) for elem in elements if elem.get("FontSize")]
        fonts = [elem.get("Font", "") for elem in elements if elem.get("Font")]
        types = [elem.get("Type", "unknown") for elem in elements]
        
        # Analyse des tailles de police
        font_size_stats = {
            "min": min(font_sizes) if font_sizes else 0,
            "max": max(font_sizes) if font_sizes else 0,
            "average": sum(font_sizes) / len(font_sizes) if font_sizes else 0,
            "unique_sizes": len(set(font_sizes)) if font_sizes else 0
        }
        
        # Analyse des polices
        font_frequency = {}
        for font in fonts:
            font_frequency[font] = font_frequency.get(font, 0) + 1
        
        # Analyse des types d'éléments
        type_frequency = {}
        for elem_type in types:
            type_frequency[elem_type] = type_frequency.get(elem_type, 0) + 1
        
        # Analyse de la distribution spatiale
        y_positions = [elem.get("Position", {}).get("y", 0) for elem in elements]
        spatial_analysis = {
            "y_range": [min(y_positions), max(y_positions)] if y_positions else [0, 0],
            "vertical_spread": max(y_positions) - min(y_positions) if y_positions else 0
        }
        
        return {
            "font_size_analysis": font_size_stats,
            "font_frequency": dict(sorted(font_frequency.items(), key=lambda x: x[1], reverse=True)[:10]),
            "element_type_frequency": type_frequency,
            "spatial_analysis": spatial_analysis,
            "total_elements_analyzed": len(elements)
        }
    
    def save_enhanced_data(self, data: Dict[str, Any]) -> None:
        """Sauvegarde les données avec analyse des métadonnées."""
        # Sauvegarde principale
        with open(self.json_output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Données avec métadonnées sauvegardées : {self.json_output_path}")
        
        # Rapport d'analyse des métadonnées
        self._print_metadata_report(data)
    
    def _print_metadata_report(self, data: Dict[str, Any]):
        """Affiche un rapport d'analyse des métadonnées."""
        analysis = data.get("metadata_analysis", {})
        elements = data.get("elements", [])
        
        print("\n" + "="*60)
        print("RAPPORT D'ANALYSE DES MÉTADONNÉES")
        print("="*60)
        
        print(f"📄 Total d'éléments extraits : {len(elements)}")
        
        # Analyse des tailles de police
        font_stats = analysis.get("font_size_analysis", {})
        print(f"\n📏 TAILLES DE POLICE :")
        print(f"   Plage : {font_stats.get('min', 0):.1f} - {font_stats.get('max', 0):.1f}")
        print(f"   Moyenne : {font_stats.get('average', 0):.1f}")
        print(f"   Tailles uniques : {font_stats.get('unique_sizes', 0)}")
        
        # Top des types d'éléments
        type_freq = analysis.get("element_type_frequency", {})
        print(f"\n🔤 TYPES D'ÉLÉMENTS DÉTECTÉS :")
        for elem_type, count in list(type_freq.items())[:5]:
            percentage = (count / len(elements)) * 100 if elements else 0
            print(f"   {elem_type}: {count} ({percentage:.1f}%)")
        
        # Polices fréquentes
        font_freq = analysis.get("font_frequency", {})
        print(f"\n🔤 POLICES PRINCIPALES :")
        for font, count in list(font_freq.items())[:3]:
            print(f"   {font}: {count} occurrences")
        
        print("="*60)
    
    def run(self) -> None:
        """Exécute l'extraction avec métadonnées exploitables."""
        try:
            logger.info("=== EXTRACTION AVEC MÉTADONNÉES EXPLOITABLES ===")
            
            # Extraction
            enhanced_data = self.extract_pdf_with_metadata()
            
            # Sauvegarde avec rapport
            self.save_enhanced_data(enhanced_data)
            
            logger.info("=== EXTRACTION TERMINÉE AVEC SUCCÈS ===")
            
        except Exception as e:
            logger.error(f"Erreur durant l'extraction : {e}")
            raise


def main():

    import argparse
    
    # Parser d'arguments optionnels
    parser = argparse.ArgumentParser(description="Extracteur PDF avec métadonnées")
    parser.add_argument('-i', '--input', help='Fichier PDF d\'entrée (override .env)')
    parser.add_argument('-o', '--output', help='Fichier JSON de sortie (override .env)')
    args = parser.parse_args()
    
    try:
        extractor = EnhancedMetadataExtractor()
        
        # Override seulement si les arguments sont fournis
        if args.input:
            extractor.pdf_input_path = args.input
        if args.output:
            extractor.json_output_path = args.output
            # Créer le dossier de sortie si nécessaire
            output_dir = Path(args.output).parent
            if output_dir != Path('.'):
                output_dir.mkdir(parents=True, exist_ok=True)
        
        extractor.run()
    except KeyboardInterrupt:
        logger.info("Processus interrompu par l'utilisateur")
        return 1
    except Exception as e:
        logger.error(f"Erreur fatale : {e}")
        return 1
    return 0



    #"""Point d'entrée principal."""
    """
    try:
        extractor = EnhancedMetadataExtractor()
        extractor.run()
    except KeyboardInterrupt:
        logger.info("Processus interrompu par l'utilisateur")
        return 1
    except Exception as e:
        logger.error(f"Erreur fatale : {e}")
        return 1
    return 0"""


if __name__ == "__main__":
    exit(main())