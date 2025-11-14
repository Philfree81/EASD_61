# 📄 Module d'Extraction Neutre

Module réutilisable pour extraire le contenu de **tout PDF** avec annotations de signatures typographiques pures.

## 🎯 Philosophie

**Pas d'interprétation sémantique** → Juste des faits bruts

- ❌ Pas de classification (session_code, abstract_title, etc.)
- ✅ Juste annotation typographique (Font_Size_Flags)
- ✅ Séquence préservée (ordre du PDF)
- ✅ Position stockée pour Step 2

## 📦 Signature Typographique

**Formule** : `Font_Size_Flags`

**Exemples** :
```
"MyriadPro-Bold_12.0_20"
"STIX-Bold_8.5_20"
"STIX-Regular_8.5_4"
"TimesNewRoman_10.0_0"
```

**Composants** :
- `Font` : Nom de la police (ex: MyriadPro-Bold)
- `Size` : Taille en points, arrondie à 1 décimale (ex: 12.0)
- `Flags` : Drapeaux typographiques (bold, italic, etc.)

## 🚀 Utilisation

### **Basique**

```bash
python neutral_extractor.py -i document.pdf -o neutral.json
```

### **Pages spécifiques**

```bash
# Pages 4 à 50
python neutral_extractor.py -i document.pdf -o neutral.json -s 4 -e 50

# À partir de la page 10
python neutral_extractor.py -i document.pdf -o neutral.json -s 10
```

### **Sans fusion**

```bash
# Garder tous les spans bruts
python neutral_extractor.py -i document.pdf -o neutral.json --no-merge
```

### **Tolérance personnalisée**

```bash
# Fusion plus permissive (5px de tolérance Y)
python neutral_extractor.py -i document.pdf -o neutral.json --y-tolerance 5.0
```

## 📊 Structure de Sortie

```json
{
  "metadata": {
    "source": "document.pdf",
    "extraction_date": "2025-01-15T14:30:00",
    "extractor": "neutral_extractor",
    "version": "1.0",
    "total_elements": 1523,
    "pages_extracted": "1-150",
    "merge_consecutive": true
  },
  
  "signature_catalog": {
    "MyriadPro-Bold_12.0_20": {
      "font": "MyriadPro-Bold",
      "size": 12.0,
      "flags": 20,
      "count": 45,
      "examples": ["OP 01", "OP 02", "SO 068"]
    },
    "STIX-Bold_8.5_20": {
      "font": "STIX-Bold",
      "size": 8.5,
      "flags": 20,
      "count": 230,
      "examples": ["1181", "1182", "Glycaemic overtreatment"]
    }
  },
  
  "elements": [
    {
      "id": 0,
      "page": 4,
      "text": "OP 01",
      "signature": "MyriadPro-Bold_12.0_20",
      "position": {
        "x": 51.0,
        "y": 54.0,
        "w": 29.5,
        "h": 12.0
      }
    },
    {
      "id": 1,
      "page": 4,
      "text": "Influencing cardiovascular outcomes",
      "signature": "MyriadPro-Bold_12.0_20",
      "position": {
        "x": 82.0,
        "y": 54.0,
        "w": 238.0,
        "h": 12.0
      },
      "_merged_count": 3
    }
  ]
}
```

## 🔀 Fusion des Éléments Consécutifs

### **Critères de Fusion**

Deux éléments consécutifs sont fusionnés si **TOUS** ces critères sont vrais :

1. ✅ **Même signature** typographique
2. ✅ **Même page**
3. ✅ **Proximité Y** (< 3px par défaut)
4. ✅ **Continuité X** (gap < 50px)

### **Exemple de Fusion**

**Avant fusion** (3 spans) :
```json
[
  {"id": 0, "text": "This", "signature": "S1", "position": {"x": 51, "y": 100}},
  {"id": 1, "text": "is", "signature": "S1", "position": {"x": 72, "y": 100}},
  {"id": 2, "text": "text", "signature": "S1", "position": {"x": 90, "y": 100}}
]
```

**Après fusion** (1 élément) :
```json
[
  {
    "id": 0,
    "text": "This is text",
    "signature": "S1",
    "position": {"x": 51, "y": 100, "w": 55, "h": 12},
    "_merged_count": 3
  }
]
```

### **Ce qui N'EST PAS fusionné**

❌ Colonnes différentes (gap X > 50px)
```
"OP 01" (x=51) et "OP 02" (x=306)
→ Gap = 255px → PAS fusionné
```

❌ Lignes différentes (gap Y > 3px)
```
"Line 1" (y=100) et "Line 2" (y=112)
→ Gap = 12px → PAS fusionné
```

❌ Signatures différentes
```
"Bold text" (STIX-Bold) et "Regular text" (STIX-Regular)
→ Signatures différentes → PAS fusionné
```

## 🔍 Catalogue des Signatures

Le `signature_catalog` vous permet de :

### **Identifier les styles utilisés**

```python
import json

with open('neutral.json') as f:
    data = json.load(f)

# Quelles signatures existent ?
for sig, details in data['signature_catalog'].items():
    print(f"{sig}: {details['count']} occurrences")
```

### **Analyser la distribution**

```python
import matplotlib.pyplot as plt

signatures = list(data['signature_catalog'].keys())
counts = [details['count'] for details in data['signature_catalog'].values()]

plt.barh(signatures[:10], counts[:10])
plt.xlabel('Nombre d\'éléments')
plt.title('Top 10 Signatures')
plt.show()
```

### **Explorer les exemples**

```python
# Voir des exemples pour une signature
sig = "STIX-Bold_8.5_20"
examples = data['signature_catalog'][sig]['examples']
print(f"Exemples de {sig}:")
for ex in examples:
    print(f"  - {ex}")
```

## 📍 Position des Éléments

Chaque élément contient sa position **minimale** :

```json
"position": {
  "x": 51.0,    // Coordonnée X (gauche)
  "y": 54.0,    // Coordonnée Y (haut)
  "w": 29.5,    // Largeur
  "h": 12.0     // Hauteur
}
```

**Utilité en Step 2** :
- Déterminer les colonnes (`x` ~51 ou ~306)
- Détecter les alignements
- Calculer les distances entre éléments
- Reconstruire la mise en page

## 🧪 Validation des Résultats

### **Vérifier le catalogue**

```bash
# Compter les signatures
cat neutral.json | python -c "import json,sys; d=json.load(sys.stdin); print(f\"Signatures: {len(d['signature_catalog'])}\")"
```

### **Trouver une signature spécifique**

```python
import json

with open('neutral.json') as f:
    data = json.load(f)

# Chercher tous les "MyriadPro-Bold"
for elem in data['elements']:
    if 'MyriadPro-Bold' in elem['signature']:
        print(f"Page {elem['page']}: {elem['text'][:50]}")
```

### **Analyser la séquence**

```python
# Voir la séquence de signatures
for i in range(min(20, len(data['elements']))):
    elem = data['elements'][i]
    print(f"{i:3}: {elem['signature']:30} | {elem['text'][:40]}")
```

## 💡 Use Cases

### **1. Analyse Exploratoire**

Avant de coder Step 2, analysez le `neutral.json` :
- Quelles signatures sont présentes ?
- Quelle est leur distribution ?
- Quels exemples pour chaque signature ?

### **2. Prototypage de Règles**

```python
# Prototypage rapide des règles Step 2
elements = data['elements']

# Règle : "MyriadPro-Bold à x=51 → session_code"
for elem in elements:
    if (elem['signature'].startswith('MyriadPro-Bold') and
        abs(elem['position']['x'] - 51) < 10):
        print(f"Session code détecté: {elem['text']}")
```

### **3. Base Commune Multi-Projets**

Le même `neutral_extractor.py` pour :
- Diabetologia abstracts
- Lancet papers
- NEJM supplements
- Vos propres formats

→ Seul Step 2 change (règles spécifiques)

## 🐛 Troubleshooting

### Trop de signatures différentes

```bash
# Essayer avec fusion désactivée
python neutral_extractor.py -i doc.pdf -o neutral.json --no-merge
```

### Fusion trop agressive

```bash
# Réduire la tolérance Y
python neutral_extractor.py -i doc.pdf -o neutral.json --y-tolerance 1.0
```

### Éléments manquants

Vérifier que PyMuPDF détecte bien tout :
```python
import fitz
doc = fitz.open('doc.pdf')
page = doc[3]  # Page 4
text_dict = page.get_text("dict")
print(json.dumps(text_dict, indent=2))
```

## 🔄 Intégration avec Step 2

```python
# Step 2 : Charger les données neutres
import json

with open('neutral.json') as f:
    neutral_data = json.load(f)

# Appliquer vos règles sémantiques
for elem in neutral_data['elements']:
    if elem['signature'] == 'MyriadPro-Bold_12.0_20':
        if abs(elem['position']['x'] - 51) < 10:
            elem['semantic_type'] = 'session_code'
    
    elif elem['signature'] == 'STIX-Bold_8.5_20':
        if is_numeric(elem['text']):
            elem['semantic_type'] = 'abstract_code'

# Sauvegarder enrichi
with open('semantic.json', 'w') as f:
    json.dump(neutral_data, f, indent=2)
```

## ⚙️ API Python

```python
from neutral_extractor import NeutralExtractor

# Initialisation
extractor = NeutralExtractor(
    merge_consecutive=True,
    y_tolerance=3.0
)

# Extraction
data = extractor.extract_from_pdf(
    pdf_path='document.pdf',
    start_page=4,
    end_page=50
)

# Accès aux données
print(f"Total éléments: {len(data['elements'])}")
print(f"Signatures: {len(data['signature_catalog'])}")

# Sauvegarder
extractor.save_to_json(data, 'output.json')
```

## 📝 Notes Importantes

1. **Réutilisable** : Même code pour tous vos PDFs
2. **Neutre** : Aucune interprétation sémantique
3. **Séquentiel** : Ordre du PDF préservé
4. **Positionné** : Coordonnées disponibles
5. **Catalogue** : Vue d'ensemble des styles

---

**Ce module est la fondation réutilisable. Step 2 appliquera vos règles spécifiques.** 🎯
