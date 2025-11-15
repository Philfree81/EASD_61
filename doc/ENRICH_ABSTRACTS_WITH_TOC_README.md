# 📄 Enrichissement des Abstracts avec Table des Matières

Script pour enrichir `neutral_typed_pass3c.json` avec les sections et sessions extraites de `metadata.json`.

## 🎯 Objectif

Ce script fusionne les données de deux fichiers :
- **`metadata.json`** : Contient la table des matières (sections, subsections, sessions)
- **`neutral_typed_pass3c.json`** : Contient les abstracts structurés

Le résultat est un fichier enrichi qui contient (dans cet ordre) :
- `metadata` : Métadonnées du document (DOI, journal, dates, etc.)
- `abstracts` : Tous les abstracts existants
- `section_TOC` : Table des matières complète avec hiérarchie
- `sessions` : Liste consolidée de toutes les sessions

## 🚀 Utilisation

### **Basique**

```bash
python scripts/enrich_abstracts_with_toc.py \
  -m metadata.json \
  -a neutral_typed_pass3c.json \
  -o neutral_typed_pass3c_enriched.json
```

### **Avec chemins relatifs**

```bash
python scripts/enrich_abstracts_with_toc.py \
  -m ./metadata.json \
  -a ./neutral_typed_pass3c.json \
  -o ./out/neutral_typed_pass3c_enriched.json
```

## 📊 Structure des Fichiers

### **Entrée : metadata.json**

```json
{
  "metadata": { ... },
  "table_of_contents": {
    "sections": [
      {
        "name": "Abstracts",
        "level": 1,
        "subsections": [
          {
            "name": "Index of Oral Presentations",
            "level": 2,
            "sessions": [
              {
                "code": "OP 01",
                "title": "Influencing cardiovascular outcomes..."
              }
            ]
          }
        ]
      }
    ]
  },
  "sessions": [
    {
      "code": "OP 01",
      "title": "Influencing cardiovascular outcomes...",
      "section": "Abstracts",
      "subsection": "Index of Oral Presentations"
    }
  ]
}
```

### **Entrée : neutral_typed_pass3c.json**

```json
{
  "abstracts": [
    {
      "abstract_id": "abs_0002",
      "abstract_code": "2",
      "title": "...",
      "authors": [ ... ],
      "institutions": [ ... ],
      "sections": { ... }
    }
  ]
}
```

### **Sortie : neutral_typed_pass3c_enriched.json**

```json
{
  "metadata": {
    "DOI": "10.1007",
    "DOI_num_editeur": "1007",
    "DOI_num_doc": "s00125-025-06497-1",
    "lien_doi": "https://doi.org/10.1007/s00125-025-06497-1",
    "year": 2025,
    "journal": "Diabetologia",
    "page_interne_debut": "S1",
    "page_interne_fin": "S754",
    "tech_document_name": "Diabetologia (2025) 68 (Suppl 1):S1–S754",
    "nature_contenu": "ABSTRACTS",
    "doc_title": "61st EASD Annual Meeting...",
    "event_city": "Vienna, Austria",
    "date_event_start": "2025-09-15",
    "date_event_end": "2025-09-19"
  },
  "abstracts": [
    {
      "abstract_id": "abs_0002",
      "abstract_code": "2",
      "title": "...",
      "authors": [ ... ],
      "institutions": [ ... ],
      "sections": { ... }
    }
  ],
  "section_TOC": {
    "sections": [
      {
        "name": "Abstracts",
        "level": 1,
        "subsections": [ ... ]
      }
    ]
  },
  "sessions": [
    {
      "code": "OP 01",
      "title": "Influencing cardiovascular outcomes...",
      "section": "Abstracts",
      "subsection": "Index of Oral Presentations"
    }
  ]
}
```

## 🔍 Fonctionnalités

### **1. Extraction des Métadonnées**

Le script extrait la clé `metadata` de `metadata.json` et l'ajoute en **première position** dans le fichier enrichi (en-tête du document).

### **2. Extraction de la Table des Matières**

Le script extrait la clé `table_of_contents` de `metadata.json` et l'ajoute comme `section_TOC` dans le fichier enrichi.

### **3. Extraction des Sessions**

Le script extrait la liste des sessions de deux façons :
- Si `metadata.json` contient une clé `sessions`, elle est utilisée directement
- Sinon, les sessions sont construites à partir de `table_of_contents`

### **4. Préservation des Données**

Tous les abstracts existants sont préservés sans modification. Les nouvelles clés sont ajoutées au niveau racine dans l'ordre suivant :
1. `metadata` (en-tête)
2. `abstracts` (contenu principal)
3. `section_TOC` (structure organisationnelle)
4. `sessions` (référence rapide)

## 💡 Cas d'Usage

### **1. Enrichissement Standard**

```bash
# Générer metadata.json d'abord
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o metadata.json

# Enrichir les abstracts
python scripts/enrich_abstracts_with_toc.py \
  -m metadata.json \
  -a neutral_typed_pass3c.json \
  -o neutral_typed_pass3c_enriched.json
```

### **2. Pipeline Complet**

```bash
# 1. Analyser les pages d'introduction
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o metadata.json

# 2. Extraire et typer les abstracts (pass 1, 2, 3)
python scripts/semantic_typing_pass_1.py ...
python scripts/semantic_typing_pass_2.py ...
python scripts/semantic_typing_pass_3.py ...

# 3. Enrichir avec la table des matières
python scripts/enrich_abstracts_with_toc.py \
  -m metadata.json \
  -a neutral_typed_pass3c.json \
  -o neutral_typed_pass3c_enriched.json
```

### **3. Utilisation Programmatique**

```python
from scripts.enrich_abstracts_with_toc import (
    load_json_file,
    extract_table_of_contents,
    extract_sessions,
    enrich_abstracts_file
)
from pathlib import Path

# Charger les fichiers
metadata = load_json_file(Path("metadata.json"))
abstracts = load_json_file(Path("neutral_typed_pass3c.json"))

# Extraire les données
toc = extract_table_of_contents(metadata)
sessions = extract_sessions(metadata)

# Enrichir
enriched = enrich_abstracts_file(abstracts, toc, sessions)

# Sauvegarder
with open("enriched.json", "w") as f:
    json.dump(enriched, f, indent=2)
```

## 🔄 Structure des Données Ajoutées

### **section_TOC**

Contient la hiérarchie complète :
- **Niveau 1** : Sections principales (ex: "Abstracts", "Late-Breaking Abstracts")
- **Niveau 2** : Sous-sections (ex: "Index of Oral Presentations")
- **Niveau 3** : Sessions individuelles (code + titre)

### **sessions**

Liste plate de toutes les sessions avec :
- `code` : Code de la session (ex: "OP 01", "SO 068")
- `title` : Titre de la session
- `section` : Section parente (ex: "Abstracts")
- `subsection` : Sous-section parente (ex: "Index of Oral Presentations")

## 🐛 Troubleshooting

### **Erreur : "metadata.json doit contenir une clé 'table_of_contents'"**

**Cause** : Le fichier `metadata.json` n'a pas la structure attendue.

**Solution** : Vérifiez que `metadata.json` a été généré avec `analyze_intro_pages.py` :
```bash
python scripts/analyze_intro_pages.py -i your_pdf.pdf -o metadata.json
```

### **Erreur : "Fichier non trouvé"**

**Solution** : Vérifiez les chemins des fichiers :
```bash
# Vérifier que les fichiers existent
ls -la metadata.json
ls -la neutral_typed_pass3c.json
```

### **Sessions manquantes**

Si `metadata.json` n'a pas de clé `sessions`, le script les construit automatiquement depuis `table_of_contents`. Vérifiez que `table_of_contents` contient bien les sessions.

## 📝 Notes

1. **Préservation** : Le script ne modifie pas les abstracts existants, il ajoute seulement les nouvelles clés.

2. **Ordre** : L'ordre des abstracts dans le fichier enrichi reste identique à l'original.

3. **Format** : Le fichier de sortie utilise un indentation de 2 espaces pour la lisibilité.

4. **Encodage** : Tous les fichiers sont traités en UTF-8.

## ✅ Checklist

- [ ] `metadata.json` généré avec `analyze_intro_pages.py`
- [ ] `neutral_typed_pass3c.json` existe et contient des abstracts
- [ ] Fichier enrichi généré avec succès
- [ ] `section_TOC` présent dans le fichier enrichi
- [ ] `sessions` présent dans le fichier enrichi
- [ ] Tous les abstracts préservés

---

**Ce script complète le pipeline en ajoutant la structure organisationnelle (table des matières) aux abstracts extraits.** 🎯

