#!/usr/bin/env python3
"""
Analyse des signatures typographiques depuis neutral.json
Produit deux vues : par fréquence et par taille
Export terminal + CSV
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
import argparse


def load_neutral_json(json_path: str) -> dict:
    """Charge le fichier neutral.json"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_signatures(data: dict) -> dict:
    """
    Analyse les signatures du catalog
    
    Returns:
        dict avec signatures enrichies (+ stats position, colonnes...)
    """
    catalog = data.get('signature_catalog', {})
    elements = data.get('elements', [])
    total_texts = data['metadata'].get('total_texts', len(elements))
    
    # Enrichir avec stats de position
    enriched = {}
    
    for sig, details in catalog.items():
        # Trouver tous les éléments avec cette signature
        sig_elements = [e for e in elements if e.get('signature') == sig]
        
        # Stats position
        pages = set(e['page'] for e in sig_elements)
        left_count = sum(1 for e in sig_elements if e.get('line_position') == 'left')
        right_count = sum(1 for e in sig_elements if e.get('line_position') == 'right')
        
        enriched[sig] = {
            'font': details['font'],
            'size': details['size'],
            'flags': details['flags'],
            'count': details['count'],
            'percentage': (details['count'] / total_texts * 100) if total_texts > 0 else 0,
            'examples': details['examples'],
            'pages': sorted(pages),
            'left_count': left_count,
            'right_count': right_count
        }
    
    return enriched


def print_frequency_view(signatures: dict):
    """Affiche la vue par fréquence"""
    print("\n" + "="*80)
    print("📊 VUE PAR FRÉQUENCE (Top → Moins utilisées)")
    print("="*80)
    
    # Trier par fréquence décroissante
    sorted_sigs = sorted(signatures.items(), key=lambda x: x[1]['count'], reverse=True)
    
    print(f"\n{'#':<4} {'Signature':<40} {'Count':<8} {'%':<8} {'Exemple'}")
    print("-"*80)
    
    for i, (sig, details) in enumerate(sorted_sigs, 1):
        example = details['examples'][0][:35] if details['examples'] else ""
        print(f"{i:<4} {sig:<40} {details['count']:<8} {details['percentage']:>6.1f}%  {example}...")


def print_size_view(signatures: dict):
    """Affiche la vue par taille (groupée)"""
    print("\n" + "="*80)
    print("📏 VUE PAR TAILLE (Grandes → Petites)")
    print("="*80)
    
    # Grouper par catégorie de taille
    large = {}    # >= 12.0
    medium = {}   # 8.0 - 11.9
    small = {}    # < 8.0
    
    for sig, details in signatures.items():
        size = details['size']
        if size >= 12.0:
            large[sig] = details
        elif size >= 8.0:
            medium[sig] = details
        else:
            small[sig] = details
    
    # Afficher chaque catégorie
    categories = [
        ("📌 GRANDES (≥ 12.0pt) - Probablement TITRES", large),
        ("📝 MOYENNES (8.0-11.9pt) - Probablement CORPS DE TEXTE", medium),
        ("🔤 PETITES (< 8.0pt) - Probablement EXPOSANTS/NOTES", small)
    ]
    
    for title, group in categories:
        if not group:
            continue
        
        print(f"\n{title}")
        print("-"*80)
        
        # Trier par taille décroissante dans chaque groupe
        sorted_group = sorted(group.items(), key=lambda x: x[1]['size'], reverse=True)
        
        for sig, details in sorted_group:
            example = details['examples'][0][:40] if details['examples'] else ""
            print(f"  {sig:<40} Size: {details['size']:>5.1f}pt  Count: {details['count']:>4} ({details['percentage']:>5.1f}%)")
            print(f"    Exemple: {example}...")
            print()


def print_summary(signatures: dict, metadata: dict):
    """Affiche un résumé global"""
    print("\n" + "="*80)
    print("📋 RÉSUMÉ GLOBAL")
    print("="*80)
    
    print(f"\n📄 Source: {metadata.get('source', 'N/A')}")
    print(f"📊 Total éléments: {metadata.get('total_elements', 0)}")
    print(f"   ├─ Textes: {metadata.get('total_texts', 0)}")
    print(f"   ├─ Images: {metadata.get('total_images', 0)}")
    print(f"   └─ Tables: {metadata.get('total_tables', 0)}")
    
    print(f"\n🔤 Signatures uniques détectées: {len(signatures)}")
    
    # Top 3
    top3 = sorted(signatures.items(), key=lambda x: x[1]['count'], reverse=True)[:3]
    print(f"\n🏆 Top 3 signatures:")
    for i, (sig, details) in enumerate(top3, 1):
        print(f"   {i}. {sig} ({details['count']} occurrences, {details['percentage']:.1f}%)")
    
    # Répartition par taille
    large = sum(1 for d in signatures.values() if d['size'] >= 12.0)
    medium = sum(1 for d in signatures.values() if 8.0 <= d['size'] < 12.0)
    small = sum(1 for d in signatures.values() if d['size'] < 8.0)
    
    print(f"\n📊 Répartition par taille:")
    print(f"   ├─ Grandes (≥12pt): {large} signatures")
    print(f"   ├─ Moyennes (8-12pt): {medium} signatures")
    print(f"   └─ Petites (<8pt): {small} signatures")


def export_csv(signatures: dict, output_path: str):
    """Exporte les signatures en CSV"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # En-tête
        writer.writerow([
            'signature', 
            'font', 
            'size', 
            'flags', 
            'count', 
            'percentage',
            'left_count',
            'right_count',
            'pages',
            'example1',
            'example2',
            'example3'
        ])
        
        # Trier par fréquence
        sorted_sigs = sorted(signatures.items(), key=lambda x: x[1]['count'], reverse=True)
        
        # Lignes
        for sig, details in sorted_sigs:
            examples = details['examples']
            writer.writerow([
                sig,
                details['font'],
                details['size'],
                details['flags'],
                details['count'],
                f"{details['percentage']:.2f}",
                details['left_count'],
                details['right_count'],
                ','.join(map(str, details['pages'])),
                examples[0] if len(examples) > 0 else '',
                examples[1] if len(examples) > 1 else '',
                examples[2] if len(examples) > 2 else ''
            ])
    
    print(f"\n✅ CSV exporté: {output_path}")


def export_txt(signatures: dict, metadata: dict, output_path: str):
    """Exporte un rapport texte complet"""
    with open(output_path, 'w', encoding='utf-8') as f:
        # Rediriger print vers le fichier
        import sys
        original_stdout = sys.stdout
        sys.stdout = f
        
        print("="*80)
        print("RAPPORT D'ANALYSE DES SIGNATURES TYPOGRAPHIQUES")
        print("="*80)
        print(f"\nGénéré depuis: {metadata.get('source', 'N/A')}")
        print(f"Date extraction: {metadata.get('extraction_date', 'N/A')}")
        
        # Résumé
        print_summary(signatures, metadata)
        
        # Vues
        print_frequency_view(signatures)
        print_size_view(signatures)
        
        # Restaurer stdout
        sys.stdout = original_stdout
    
    print(f"✅ Rapport texte exporté: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyse les signatures typographiques depuis neutral.json"
    )
    parser.add_argument('input', help='Fichier neutral.json en entrée')
    parser.add_argument('--csv', help='Exporter en CSV (chemin de sortie)')
    parser.add_argument('--txt', help='Exporter rapport texte (chemin de sortie)')
    parser.add_argument('--export', help='Exporter CSV et TXT avec ce préfixe (ex: report)')
    
    args = parser.parse_args()
    
    # Vérifier existence fichier
    if not Path(args.input).exists():
        print(f"❌ Erreur: Fichier non trouvé: {args.input}")
        return 1
    
    # Charger données
    print(f"📂 Chargement de {args.input}...")
    data = load_neutral_json(args.input)
    
    # Analyser signatures
    print("🔍 Analyse des signatures...")
    signatures = analyze_signatures(data)
    metadata = data['metadata']
    
    # Affichage terminal
    print_summary(signatures, metadata)
    print_frequency_view(signatures)
    print_size_view(signatures)
    
    # Exports
    if args.export:
        # Export avec préfixe
        csv_path = f"{args.export}.csv"
        txt_path = f"{args.export}.txt"
        export_csv(signatures, csv_path)
        export_txt(signatures, metadata, txt_path)
    else:
        # Exports individuels
        if args.csv:
            export_csv(signatures, args.csv)
        if args.txt:
            export_txt(signatures, metadata, args.txt)
    
    print("\n" + "="*80)
    print("✅ Analyse terminée !")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    exit(main())
