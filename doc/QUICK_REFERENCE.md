# 📋 Neutral Extractor - Quick Reference

## 🎯 En bref

**Extracteur PDF neutre et généraliste** qui capture TOUT sans interpréter.

```
PDF → Neutral Extractor → JSON structuré + Images
                          ↓
                     Couche sémantique (future)
```

---

## ⚡ Usage rapide

```bash
# Installation
pip install PyMuPDF

# Extraction
python neutral_extractor.py -i document.pdf -o output.json

# Résultat
output.json          # Données structurées
output_images/       # Images extraites
```

---

## 📊 Structure JSON (simplifié)

```json
{
  "metadata": {
    "total_elements": 450,
    "total_texts": 420,
    "total_images": 5,
    "total_tables": 0
  },
  
  "signature_catalog": {
    "MyriadPro-Bold_12.0_20": {
      "count": 45,
      "examples": ["Titre exemple"]
    }
  },
  
  "elements": [
    {
      "id": 0,
      "type": "text",
      "page": 3,
      "text": "Contenu",
      "signature": "MyriadPro-Bold_12.0_20",
      "position": {"x": 51, "y": 100, "w": 200, "h": 15},
      "line_id": "p3_L10",
      "line_num": 10,
      "line_start": true,
      "line_position": "left"
    }
  ]
}
```

---

## 🔑 Champs clés

| Champ | Description | Exemple |
|-------|-------------|---------|
| `type` | Type d'élément | `"text"`, `"image"`, `"table"` |
| `signature` | Signature typo | `"MyriadPro-Bold_12.0_20"` |
| `line_id` | ID de ligne | `"p3_L10"` |
| `line_num` | N° de ligne | `10` |
| `line_position` | Colonne | `"left"` ou `"right"` |
| `line_start` | Début ligne ? | `true` / `false` |

---

## 🎨 Signatures typographiques

**Format :** `"FontName_Size_Flags"`

**Exemples :**
```
MyriadPro-Bold_12.0_20    → Titre en gras 12pt
STIX-Regular_8.5_4        → Corps de texte 8.5pt
STIX-Regular_5.9_5        → Exposant 5.9pt
```

**Usage :**
```python
# Filtrer par signature
titles = [e for e in elements if e['signature'] == 'MyriadPro-Bold_12.0_20']
```

---

## 📍 Système de lignes

**Colonnes :**
- `X < 305` → `"left"`
- `X >= 305` → `"right"`

**Ordre de lecture :**
1. Colonne GAUCHE (haut → bas)
2. Colonne DROITE (haut → bas)

**line_num :**
- Compteur global par page
- Recommence à 0 sur chaque page

---

## 🔍 Filtres courants

```python
# Par type
texts = [e for e in elements if e.get('type') == 'text']
images = [e for e in elements if e.get('type') == 'image']

# Par page
page_3 = [e for e in elements if e['page'] == 3]

# Par colonne
left = [e for e in elements if e.get('line_position') == 'left']

# Par signature
titles = [e for e in texts if e['signature'] == 'Bold_12.0_20']

# Débuts de ligne
starts = [e for e in elements if e.get('line_start') == True]
```

---

## 🖼️ Images

```json
{
  "type": "image",
  "image_id": "p3_img0",
  "image_file": "output_images/p3_img0.jpeg",
  "format": "jpeg",
  "size": {"width": 800, "height": 600}
}
```

**Fichiers :**
```
output_images/
├── p3_img0.jpeg
├── p3_img1.png
└── p4_img0.jpeg
```

---

## ⚙️ Options CLI

```bash
python neutral_extractor.py \
  -i input.pdf \           # PDF source
  -o output.json \         # JSON sortie
  -s 1 \                   # Page début
  -e 10 \                  # Page fin
  --no-merge \             # Pas de fusion spans
  --y-tolerance 5.0        # Tolérance ligne
```

---

## 📈 Rapport terminal

```
📊 Total éléments : 450
   ├─ Textes : 420
   ├─ Images : 5
   └─ Tables : 0

🔤 SIGNATURES TYPOGRAPHIQUES : 12
   1. STIX-Regular_8.5_4 (156, 37.1%)
   2. STIX-Bold_8.5_20 (89, 21.2%)
   ...

📍 STATISTIQUES DE LIGNE :
   Colonnes : Left=245 | Right=175
   Débuts de ligne : 85
   Exposants rattachés : 42

🖼️  IMAGES : 5
```

---

## 🎯 Workflow typique

```
1. Extraction
   → python neutral_extractor.py -i doc.pdf -o out.json

2. Exploration
   → Analyser signature_catalog
   → Identifier les patterns

3. Documentation
   → Noter les signatures importantes
   → Documenter la structure

4. Couche sémantique (future)
   → Créer rules.yaml
   → Mapper signatures → rôles sémantiques
```

---

## 💡 Cas d'usage rapides

**Extraire tous les titres :**
```python
titles = [e for e in elements 
          if 'Bold' in e.get('signature', '') 
          and e['text'].isupper()]
```

**Reconstruire colonne gauche :**
```python
left_text = "\n".join(
    e['text'] for e in elements 
    if e.get('line_position') == 'left'
)
```

**Lister les images :**
```python
for img in elements:
    if img.get('type') == 'image':
        print(f"{img['image_id']}: {img['image_file']}")
```

---

## ⚠️ Important

### ✅ Ce que ça fait
- Extrait **tout** le contenu
- Préserve les **positions exactes**
- Détecte les **patterns typo**

### ❌ Ce que ça ne fait PAS
- **Pas d'interprétation** (pas de "titre" automatique)
- **Pas d'OCR** (texte dans images)
- **Pas de reconstruction** tables-images

---

## 🔧 Paramètres clés

| Paramètre | Défaut | Impact |
|-----------|--------|--------|
| `merge_consecutive` | `True` | Fusionne spans consécutifs |
| `y_tolerance` | `3.0` | Tolérance ligne (fusion) |
| `X_THRESHOLD` | `305` | Seuil colonnes left/right |
| Exposants | `h<9 or size<7` | Détection auto |

---

## 🚀 Next Steps

1. ✅ **Extraction neutre** (ce script)
2. 🔜 **Règles d'interprétation** (YAML)
3. 🔜 **Extracteur sémantique** (script suivant)

---

**📖 Documentation complète : `README_NEUTRAL_EXTRACTOR.md`**
