# 📄 Générateur de Markdown pour Abstracts (Pass 3)

Script pour générer des fichiers Markdown formatés à partir des abstracts structurés (format pass3).

## 🎯 Objectif

Convertir les abstracts extraits et structurés (format JSON pass3) en fichiers Markdown lisibles, avec un formatage similaire aux abstracts scientifiques originaux.

## 🚀 Utilisation

### **Basique (150 abstracts par fichier)**

```bash
python scripts/generate_abstracts_markdown.py \
  -i neutral_typed_pass3c.json \
  -o abstracts.md
```

Le script génère automatiquement plusieurs fichiers si nécessaire :
- `abstracts_part001.md` (abstracts 1-150)
- `abstracts_part002.md` (abstracts 151-300)
- `abstracts_part003.md` (abstracts 301-450)
- etc.

### **Avec options**

```bash
# Changer le nombre d'abstracts par fichier (ex: 100)
python scripts/generate_abstracts_markdown.py \
  -i neutral_typed_pass3c.json \
  -o abstracts.md \
  --per-file 100

# Inclure les abstracts WITHDRAWN
python scripts/generate_abstracts_markdown.py \
  -i neutral_typed_pass3c.json \
  -o abstracts.md \
  --include-withdrawn

# Combinaison des options
python scripts/generate_abstracts_markdown.py \
  -i neutral_typed_pass3c.json \
  -o abstracts.md \
  --per-file 200 \
  --include-withdrawn
```

## 📊 Format de Sortie

Le script génère un ou plusieurs fichiers Markdown (150 abstracts par fichier par défaut) avec le format suivant :

```markdown
# Abstracts

*Généré à partir de neutral_typed_pass3c.json*
*Partie 1 sur 3 (abstracts 1 à 150)*

---

**2**

**Oral semaglutide and cardiovascular outcomes by baseline A1c and BMI in people with type 2 diabetes in the SOUL trial**

S.E. Inzucchi, O. Kleist Jeppesen, K. Mandavya, J.F.E. Mann, N. Marx, D.K. McGuire, S.L. Mulvagh, R. Pop-Busui, N.R. Poulter, M.S. Ripa, J.B. Buse, on behalf of the SOUL study group

1. Yale University School of Medicine, New Haven, CT, USA, Insti-
3. UK, Novo Nordisk A/S, Søborg, Denmark, Novo Nordisk Service
5. Centre India Pvt Ltd, Bangalore, India, Friedrich Alexander University
...

**Background and aims:**
In SOUL, oral semaglutide 14 mg once a day (QD), a glucagon-like peptide-1 receptor agonist (GLP-1 RA), reduced major adverse cardiovascular (CV) event (MACE) risk by 14%...

**Materials and methods:**
SOUL's primary outcome was time to first MACE, assessed for this post hoc analysis by baseline HbA1c, BMI and body weight using Cox regression.

**Results:**
People with T2D (n=9650; HbA1c 6.5–10%) and known atherosclerotic CV disease (ASCVD) or chronic kidney disease (CKD) were randomized...

**Conclusion:**
In SOUL, the CV benefits of oral semaglutide appeared more pronounced with higher HbA1c levels at baseline...

**Disclosure:**
S.E. Inzucchi: Employment/Consultancy; Novo Nordisk, Astra Zeneca...

---
```

## 📋 Structure d'un Abstract dans le Markdown

Chaque abstract contient :

1. **Numéro de l'abstract** : `**2**` (en gras)
2. **Titre** : `**Titre de l'abstract**` (en gras)
3. **Auteurs** : Liste séparée par des virgules
4. **Institutions** : Liste numérotée avec indices
5. **Sections** :
   - **Background and aims:**
   - **Materials and methods:**
   - **Results:**
   - **Conclusion:**
   - **Disclosure:**

## 🔍 Format d'Entrée (JSON Pass3)

Le script attend un fichier JSON avec la structure suivante :

```json
{
  "abstracts": [
    {
      "abstract_id": "abs_0002",
      "abstract_code": "2",
      "page_start": 3,
      "page_end": 4,
      "title": "Titre de l'abstract",
      "authors": [
        {
          "name": "Auteur 1",
          "indices": []
        }
      ],
      "institutions": [
        {
          "index": 1,
          "text": "Institution 1"
        }
      ],
      "sections": {
        "background_and_aims": "Texte...",
        "materials_and_methods": "Texte...",
        "results": "Texte...",
        "conclusion": "Texte...",
        "disclosure_text": "Texte..."
      }
    }
  ]
}
```

## 💡 Cas d'Usage

### **1. Générer un fichier Markdown complet**

```bash
python scripts/generate_abstracts_markdown.py \
  -i neutral_typed_pass3c.json \
  -o all_abstracts.md
```

### **2. Filtrer et générer (avec script Python)**

```python
import json
from pathlib import Path
from scripts.generate_abstracts_markdown import format_abstract

# Charger le JSON
with open('neutral_typed_pass3c.json') as f:
    data = json.load(f)

# Filtrer par mot-clé dans le titre
filtered = [
    abs for abs in data['abstracts']
    if 'diabetes' in abs.get('title', '').lower()
]

# Générer le Markdown
output = []
for abstract in filtered:
    output.append(format_abstract(abstract))
    output.append("---\n")

with open('filtered_abstracts.md', 'w') as f:
    f.write('\n'.join(output))
```

### **3. Générer un abstract spécifique**

```python
import json
from scripts.generate_abstracts_markdown import format_abstract

with open('neutral_typed_pass3c.json') as f:
    data = json.load(f)

# Trouver l'abstract par code
abstract_code = "10"
abstract = next(
    (a for a in data['abstracts'] if a.get('abstract_code') == abstract_code),
    None
)

if abstract:
    markdown = format_abstract(abstract)
    print(markdown)
```

### **4. Exporter vers différents formats**

```python
import json
from scripts.generate_abstracts_markdown import format_abstract
import csv

# Charger les abstracts
with open('neutral_typed_pass3c.json') as f:
    data = json.load(f)

# Exporter en CSV (métadonnées)
with open('abstracts_metadata.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Code', 'Title', 'Authors', 'Pages'])
    
    for abstract in data['abstracts']:
        authors = ', '.join(a.get('name', '') for a in abstract.get('authors', []))
        writer.writerow([
            abstract.get('abstract_code', ''),
            abstract.get('title', ''),
            authors,
            f"{abstract.get('page_start', '')}-{abstract.get('page_end', '')}"
        ])

# Générer le Markdown
with open('abstracts.md', 'w', encoding='utf-8') as f:
    for abstract in data['abstracts']:
        f.write(format_abstract(abstract))
        f.write("\n---\n\n")
```

## 🎨 Personnalisation

### **Modifier les titres de sections**

Éditez le dictionnaire `SECTION_TITLES` dans le script :

```python
SECTION_TITLES = {
    "background_and_aims": "Background and aims",
    "materials_and_methods": "Materials and methods",
    "results": "Results",
    "conclusion": "Conclusion",
    "disclosure_text": "Disclosure",
}
```

### **Ajouter un en-tête personnalisé**

Modifiez la fonction `process_file` :

```python
markdown_lines.append("# Mes Abstracts")
markdown_lines.append("")
markdown_lines.append(f"*Date: {datetime.now().strftime('%Y-%m-%d')}*")
markdown_lines.append("")
```

### **Formater les auteurs avec indices**

Si vous voulez afficher les indices des auteurs (quand disponibles) :

```python
def format_authors_with_indices(authors: List[Dict[str, Any]]) -> str:
    author_parts = []
    for author in authors:
        name = author.get("name", "").strip()
        indices = author.get("indices", [])
        if name:
            if indices:
                superscript = ''.join(f"^{i}" for i in indices)
                author_parts.append(f"{name}{superscript}")
            else:
                author_parts.append(name)
    return ", ".join(author_parts)
```

## 📊 Statistiques

Pour obtenir des statistiques sur les abstracts :

```python
import json

with open('neutral_typed_pass3c.json') as f:
    data = json.load(f)

abstracts = data['abstracts']

print(f"Total abstracts: {len(abstracts)}")
print(f"Avec titre: {sum(1 for a in abstracts if a.get('title'))}")
print(f"Avec auteurs: {sum(1 for a in abstracts if a.get('authors'))}")
print(f"Avec sections complètes: {sum(1 for a in abstracts if len(a.get('sections', {})) >= 4)}")
```

## 🐛 Troubleshooting

### **Erreur : "Le JSON doit contenir une clé 'abstracts'"**

Vérifiez que votre fichier JSON a la bonne structure :

```bash
python -c "import json; data=json.load(open('file.json')); print('abstracts' in data)"
```

### **Abstracts vides dans la sortie**

Les abstracts avec titre "WITHDRAWN" sont ignorés par défaut. Utilisez `--include-withdrawn` pour les inclure.

### **Problème d'encodage**

Le script utilise UTF-8. Si vous avez des problèmes :

```python
# Forcer l'encodage
with open('output.md', 'w', encoding='utf-8', errors='replace') as f:
    f.write(content)
```

## 🔄 Intégration dans le Pipeline

```bash
# Pipeline complet
python scripts/semantic_typing_pass_2.py \
  -i neutral_typed_pass1.json \
  -o neutral_typed_pass2.json

python scripts/semantic_typing_pass_3.py \
  -i neutral_typed_pass2.json \
  -o neutral_typed_pass3c.json

python scripts/generate_abstracts_markdown.py \
  -i neutral_typed_pass3c.json \
  -o abstracts.md
```

## 📝 Notes

- Les abstracts sont séparés par `---` dans le Markdown
- Les sections vides sont omises
- Les institutions sont triées par index
- Les auteurs sont formatés sans indices (les indices sont dans les institutions)

## ✅ Checklist

- [ ] Fichier JSON pass3 valide
- [ ] Markdown généré avec succès
- [ ] Format vérifié
- [ ] Sections présentes
- [ ] Encodage UTF-8 correct

---

**Ce script complète le pipeline d'extraction en générant des fichiers Markdown lisibles à partir des données structurées.** 🎯

