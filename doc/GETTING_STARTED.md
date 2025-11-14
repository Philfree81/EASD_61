# 🚀 Getting Started - Neutral Extractor

## 📋 Prérequis

### Système
- Python 3.7 ou supérieur
- pip (gestionnaire de paquets Python)

### Installation

```bash
# Installer PyMuPDF
pip install PyMuPDF

# Vérifier l'installation
python3 -c "import fitz; print(f'PyMuPDF {fitz.version[0]} installé ✓')"
```

---

## 🎯 Premier usage (5 minutes)

### Étape 1 : Télécharger le script

```bash
# Télécharger neutral_extractor.py
# (Vous l'avez déjà !)

# Vérifier qu'il fonctionne
python3 neutral_extractor.py --help
```

---

### Étape 2 : Première extraction

```bash
# Extraire un PDF
python3 neutral_extractor.py -i votre_document.pdf -o output.json

# Sortie attendue :
# 2024-11-14 10:30:00 - INFO - Ouverture du PDF : votre_document.pdf
# 2024-11-14 10:30:01 - INFO - Extraction pages 1 à 10 (sur 10)
# 2024-11-14 10:30:02 - INFO - ✓ 420 éléments texte extraits
# 2024-11-14 10:30:02 - INFO - ✓ 5 images extraites
# 2024-11-14 10:30:02 - INFO - ✓ 0 tables extraites
# ...
```

**Résultat :**
```
votre_dossier/
├── output.json              # ✓ Données structurées
└── output_images/           # ✓ Images extraites (si présentes)
    ├── p3_img0.jpeg
    └── p4_img0.png
```

---

### Étape 3 : Explorer les résultats

```bash
# Voir le rapport dans le terminal (déjà affiché)

# Ou analyser le JSON
python3 example_usage.py output.json
```

**Sortie :**
```
======================================================================
ANALYSE DE L'EXTRACTION
======================================================================

📊 Statistiques :
   Total éléments : 425
   - Textes : 420
   - Images : 5
   - Tables : 0

📄 Par page :
   Page 1: 45 textes, 0 images, 0 tables
   Page 2: 52 textes, 1 images, 0 tables
   ...

🖼️  Images extraites :
   - p3_img0: output_images/p3_img0.jpeg (Page 3, jpeg)
     Position: x=51.0, y=200.5
     Taille: 800x600px
   ...
```

---

## 📚 Tutoriel : Analyser un PDF médical

### Contexte

Vous avez un PDF d'abstract médical et vous voulez :
1. Comprendre sa structure
2. Identifier les patterns typographiques
3. Préparer l'extraction sémantique

---

### Étape 1 : Extraction complète

```bash
python3 neutral_extractor.py \
  -i medical_paper.pdf \
  -o neutral/paper1.json
```

---

### Étape 2 : Analyser le catalogue de signatures

```python
import json

# Charger le JSON
with open('neutral/paper1.json', 'r') as f:
    data = json.load(f)

catalog = data['signature_catalog']

# Afficher toutes les signatures
print("\n=== SIGNATURES DÉTECTÉES ===\n")
for sig, details in catalog.items():
    print(f"{sig}:")
    print(f"  Fréquence: {details['count']}")
    print(f"  Exemples: {details['examples'][0][:50]}...")
    print()
```

**Sortie attendue :**
```
=== SIGNATURES DÉTECTÉES ===

MyriadPro-Bold_12.0_20:
  Fréquence: 28
  Exemples: OP 01...

STIX-Bold_8.5_20:
  Fréquence: 89
  Exemples: Oral semaglutide and cardiovascular outcomes...

STIX-Regular_8.5_4:
  Fréquence: 156
  Exemples: Background: Oral semaglutide is a glucagon...

STIX-Regular_5.9_5:
  Fréquence: 42
  Exemples: 1...
```

---

### Étape 3 : Identifier les rôles

**Créer un fichier de documentation :**

```yaml
# signatures_paper1.yaml

abstract_id:
  signature: "MyriadPro-Bold_12.0_20"
  role: "Identifiant de l'abstract"
  examples:
    - "OP 01"
    - "OP 02"
  
title:
  signature: "STIX-Bold_8.5_20"
  role: "Titre de l'abstract"
  examples:
    - "Oral semaglutide and cardiovascular outcomes by baseline A1c"
  
authors:
  signature: "STIX-Bold_8.5_20"
  role: "Noms des auteurs"
  position: "after title"
  examples:
    - "S.E. Inzucchi"
  
body_text:
  signature: "STIX-Regular_8.5_4"
  role: "Corps de texte (Background, Methods, etc.)"
  
references:
  signature: "STIX-Regular_5.9_5"
  role: "Indices de référence (exposants)"
```

**💡 Conseil :** Ce fichier YAML servira de base pour créer les règles d'extraction sémantique

---

### Étape 4 : Vérifier l'ordre de lecture

```python
# Afficher les 20 premiers éléments
elements = data['elements']

print("\n=== ORDRE DE LECTURE ===\n")
for i, elem in enumerate(elements[:20]):
    line_info = f"[{elem['line_id']} {elem.get('line_position', 'N/A')}]"
    
    if elem.get('type') == 'text':
        text = elem['text'][:60]
        print(f"{i+1:3}. {line_info:15} {text}")
    elif elem.get('type') == 'image':
        print(f"{i+1:3}. {line_info:15} [IMAGE: {elem['image_id']}]")
```

**Sortie attendue :**
```
=== ORDRE DE LECTURE ===

  1. [p3_L0 left]    OP 01
  2. [p3_L1 left]    Session: Oral Presentations
  3. [p3_L2 left]    Time: Friday, November 8
  ...
 15. [p3_L14 right]  Oral semaglutide and cardiovascular outcomes by baseli
 16. [p3_L15 right]  BMI in people with type 2 diabetes in the SOUL trial
 17. [p3_L16 right]  S.E. Inzucchi
 18. [p3_L16 right]  1
 19. [p3_L16 right]  , J.E. Deanfield
 20. [p3_L16 right]  2
```

**✓ Validation :** Vérifier que l'ordre correspond au PDF original

---

### Étape 5 : Extraire une colonne

```python
# Extraire uniquement la colonne droite
right_elements = [
    e for e in elements 
    if e.get('line_position') == 'right'
    and e.get('type') == 'text'
]

# Reconstruire le texte
right_text = "\n".join(e['text'] for e in right_elements)

# Sauvegarder
with open('output_right_column.txt', 'w') as f:
    f.write(right_text)

print("✓ Colonne droite sauvegardée dans output_right_column.txt")
```

---

## 🔍 Cas d'usage avancés

### Cas 1 : Comparer plusieurs PDFs du même type

```bash
# Extraire tous les PDFs
for pdf in lot1/*.pdf; do
  name=$(basename "$pdf" .pdf)
  python3 neutral_extractor.py -i "$pdf" -o "neutral/${name}.json"
done

# Analyser les signatures communes
python3 << EOF
import json
from pathlib import Path
from collections import Counter

# Charger tous les JSON
all_signatures = Counter()

for json_file in Path('neutral').glob('*.json'):
    with open(json_file) as f:
        data = json.load(f)
        for sig in data['signature_catalog'].keys():
            all_signatures[sig] += 1

# Afficher les signatures présentes dans tous les fichiers
n_files = len(list(Path('neutral').glob('*.json')))
common = {sig: count for sig, count in all_signatures.items() if count == n_files}

print(f"\n=== SIGNATURES COMMUNES (présentes dans {n_files} fichiers) ===\n")
for sig in sorted(common.keys()):
    print(f"  - {sig}")
EOF
```

---

### Cas 2 : Extraire uniquement les images

```python
import json
import shutil
from pathlib import Path

# Charger
with open('neutral.json') as f:
    data = json.load(f)

# Créer dossier de sortie
output = Path('extracted_images')
output.mkdir(exist_ok=True)

# Copier toutes les images
for elem in data['elements']:
    if elem.get('type') == 'image':
        src = Path(elem['image_file'])
        dst = output / src.name
        shutil.copy2(src, dst)
        print(f"✓ Copié : {dst}")
```

---

### Cas 3 : Filtrer par signature

```python
# Extraire tous les titres (signature spécifique)
TITLE_SIG = "MyriadPro-Bold_12.0_20"

titles = [
    e for e in elements 
    if e.get('type') == 'text'
    and e.get('signature') == TITLE_SIG
]

print(f"\n=== TITRES DÉTECTÉS ({len(titles)}) ===\n")
for title in titles:
    print(f"Page {title['page']}, Ligne {title['line_num']}: {title['text']}")
```

---

## 🎓 Exercices pratiques

### Exercice 1 : Statistiques basiques

**Objectif :** Calculer des statistiques sur votre extraction

```python
import json

with open('output.json') as f:
    data = json.load(f)

elements = data['elements']

# TODO : Calculer
# 1. Nombre d'éléments par page
# 2. Répartition gauche/droite
# 3. Signature la plus fréquente
# 4. Nombre moyen d'éléments par ligne

# Votre code ici...
```

<details>
<summary>💡 Solution</summary>

```python
from collections import Counter

# 1. Éléments par page
by_page = Counter(e['page'] for e in elements)
print("Éléments par page:", dict(by_page))

# 2. Répartition gauche/droite
positions = Counter(e.get('line_position') for e in elements if 'line_position' in e)
print("Répartition:", dict(positions))

# 3. Signature la plus fréquente
signatures = Counter(e.get('signature') for e in elements if e.get('type') == 'text')
most_common = signatures.most_common(1)[0]
print(f"Signature la plus fréquente: {most_common[0]} ({most_common[1]} occurrences)")

# 4. Éléments par ligne
lines = Counter(e.get('line_id') for e in elements if 'line_id' in e)
avg = sum(lines.values()) / len(lines)
print(f"Moyenne par ligne: {avg:.2f} éléments")
```
</details>

---

### Exercice 2 : Reconstruction de sections

**Objectif :** Regrouper les éléments par section (Background, Methods, etc.)

```python
# TODO : Créer un dictionnaire sections
# où chaque clé est un titre de section
# et la valeur est la liste des éléments de cette section

sections = {}

# Votre code ici...
```

<details>
<summary>💡 Solution</summary>

```python
SECTION_SIG = "STIX-Bold_8.5_20"
SECTION_KEYWORDS = ["Background:", "Methods:", "Results:", "Conclusions:"]

sections = {}
current_section = None

for elem in elements:
    if elem.get('type') == 'text':
        text = elem['text']
        
        # Détecter un titre de section
        if elem.get('signature') == SECTION_SIG and any(kw in text for kw in SECTION_KEYWORDS):
            current_section = text
            sections[current_section] = []
        
        # Ajouter à la section courante
        elif current_section:
            sections[current_section].append(elem)

# Afficher
for section, content in sections.items():
    print(f"\n{section}")
    print("=" * len(section))
    for elem in content[:3]:  # 3 premiers éléments
        print(f"  {elem['text'][:80]}...")
```
</details>

---

## 🐛 Dépannage

### Problème : "ModuleNotFoundError: No module named 'fitz'"

**Solution :**
```bash
pip install PyMuPDF
# ou
pip3 install PyMuPDF
```

---

### Problème : "FileNotFoundError: PDF non trouvé"

**Solution :**
```bash
# Vérifier le chemin
ls -l votre_document.pdf

# Utiliser un chemin absolu
python3 neutral_extractor.py -i /chemin/complet/vers/document.pdf -o output.json
```

---

### Problème : "Aucune image extraite"

**Vérification :**
```python
import fitz

doc = fitz.open("document.pdf")
page = doc[0]
images = page.get_images()
print(f"Images détectées page 1: {len(images)}")

if len(images) == 0:
    print("⚠️  Pas d'images natives dans le PDF")
    print("   (Les images peuvent être vectorielles ou embeddées)")
```

---

### Problème : "Ordre de lecture incorrect"

**Solution :**
Ajuster le seuil de colonnes :

```python
# Dans neutral_extractor.py, modifier la ligne :
X_THRESHOLD = 305  # Essayer 300 ou 310

# Puis relancer
python3 neutral_extractor.py -i document.pdf -o output.json
```

---

## 📖 Ressources

### Documentation
- `README_NEUTRAL_EXTRACTOR.md` - Documentation complète
- `QUICK_REFERENCE.md` - Référence rapide
- `ARCHITECTURE.md` - Vue d'ensemble du système

### Scripts d'exemple
- `example_usage.py` - Exemples d'utilisation
- `neutral_extractor.py` - Script principal

### PyMuPDF
- Documentation : https://pymupdf.readthedocs.io/
- Tutoriels : https://pymupdf.readthedocs.io/en/latest/tutorial.html

---

## ✅ Checklist de démarrage

- [ ] Python 3.7+ installé
- [ ] PyMuPDF installé et testé
- [ ] Premier PDF extrait avec succès
- [ ] JSON exploré et compris
- [ ] Signatures documentées
- [ ] Ordre de lecture validé
- [ ] Images extraites (si présentes)

**🎉 Vous êtes prêt à passer à la couche sémantique !**

---

## 🚀 Prochaines étapes

1. ✅ **Maîtriser l'extraction neutre** (vous y êtes !)
2. 🔜 **Créer les règles YAML** (mapping signatures → rôles)
3. 🔜 **Développer l'extracteur sémantique**
4. 🔜 **Automatiser le pipeline complet**

---

**Des questions ? Consultez la documentation complète dans `README_NEUTRAL_EXTRACTOR.md`**
