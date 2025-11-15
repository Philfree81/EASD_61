# Spécification : Analyse des Pages d'Introduction (SC1)

## 📋 Vue d'ensemble

Ce document décrit le processus d'extraction et d'analyse des **premières pages** du document PDF, qui contiennent les métadonnées du document et la table des matières (index des abstracts).

**Pages concernées** : Pages 1 à 3 (ou plus selon la structure du document)

**Sous-corpus** : `SC_introduction` (distinct de `SC_session_description` qui contient les sessions et leur contenu)

---

## 🔍 Structure de la Première Page

### **En-tête (Header)**

L'en-tête de la première page contient les informations suivantes :

```
Vol.:(0123456789)1 3Diabetologia (2025) 68 (Suppl 1):S1–S754
https://doi.org/10.1007/s00125-025-06497-1

ABSTRACTS
```

#### **Champs à extraire (métadonnées du document)**

Ces champs concernent le **document entier** et seront stockés dans la partie `metadata` du document JSON :

| Champ | Exemple | Description |
|-------|---------|-------------|
| `tech_document_name` | `Diabetologia (2025) 68 (Suppl 1):S1–S754` | Nom technique complet du document |
| `page_interne_debut` | `S1` | Première page interne (format S1, S2, etc.) |
| `page_interne_fin` | `S754` | Dernière page interne |
| `year` | `2025` | Année de publication |
| `DOI_num_editeur` | `1007` | Numéro d'éditeur dans le DOI |
| `DOI_num_doc` | `s00125-025-06497-1` | Numéro de document dans le DOI |
| `lien_doi` | `https://doi.org/10.1007/s00125-025-06497-1` | Lien DOI complet |
| `journal` | `Diabetologia` | Nom du journal |
| `DOI` | `10.1007` | Préfixe DOI |
| `nature_contenu` | `ABSTRACTS` | Nature du contenu (toujours "ABSTRACTS" ici) |

---

### **Corps de la Page**

#### **1. Titre de l'événement**

```
61st EASD Annual Meeting of the European Association for the Study of Diabetes
```

**Champ à extraire** :
- `doc_title` : Titre complet de l'événement

#### **2. Lieu et dates**

```
Vienna, Austria, 15 - 19 September 2025
```

**Champs à extraire** :
- `event_city` : Ville de l'événement (ex: `Vienna, Austria`)
- `date_event_start` : Date de début (ex: `2025-09-15`)
- `date_event_end` : Date de fin (ex: `2025-09-19`)

#### **3. Table des matières (Index)**

La table des matières présente une **hiérarchie de sections** :

```
Abstracts
├── Index of Oral Presentations
│   ├── OP 01 Influencing cardiovascular outcomes: medications and behaviours
│   ├── OP 02 Novel risk factors for type 2 diabetes
│   └── ...
├── Index of Short Oral Discussions
│   ├── SO 068 Dietary diversity in practice: navigating multiple nutritional approaches
│   └── ...
│
Late-Breaking Abstracts
├── Index of LBA Oral Presentations
│   └── ...
└── Index of LBA Short Oral Discussions
    └── ...
```

**Structure hiérarchique** :

1. **Niveau 1** : Sections principales
   - `Abstracts`
   - `Late-Breaking Abstracts`

2. **Niveau 2** : Types de présentations
   - `Index of Oral Presentations`
   - `Index of Short Oral Discussions`
   - `Index of LBA Oral Presentations`
   - `Index of LBA Short Oral Discussions`

3. **Niveau 3** : Sessions individuelles
   - Format : `CODE TITRE` (ex: `OP 01 Influencing cardiovascular outcomes...`)
   - **Code session** : 5-6 caractères (ex: `OP 01`, `SO 068`)
   - **Titre session** : Reste de la ligne

**Cas particuliers** :
- Certaines sessions sont marquées `WITHDRAWN` → Le titre de la session devient `WITHDRAWN`

---

## 🚫 Éléments à Exclure

Les éléments suivants doivent être **exclus** de l'analyse (header/footer) :

- `© The Author(s), under exclusive licence to Springer-Verlag GmbH GmbH Germany, part of Springer Nature 2025`
- Autres éléments de header/footer standard

---

## 📊 Données à Extraire

### **1. Métadonnées du Document**

Structure JSON pour les métadonnées :

```json
{
  "metadata": {
    "tech_document_name": "Diabetologia (2025) 68 (Suppl 1):S1–S754",
    "page_interne_debut": "S1",
    "page_interne_fin": "S754",
    "year": 2025,
    "DOI_num_editeur": "1007",
    "DOI_num_doc": "s00125-025-06497-1",
    "lien_doi": "https://doi.org/10.1007/s00125-025-06497-1",
    "journal": "Diabetologia",
    "DOI": "10.1007",
    "nature_contenu": "ABSTRACTS",
    "doc_title": "61st EASD Annual Meeting of the European Association for the Study of Diabetes",
    "event_city": "Vienna, Austria",
    "date_event_start": "2025-09-15",
    "date_event_end": "2025-09-19"
  }
}
```

### **2. Table des Matières**

Structure JSON pour la table des matières :

```json
{
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
                "title": "Influencing cardiovascular outcomes: medications and behaviours"
              },
              {
                "code": "OP 02",
                "title": "Novel risk factors for type 2 diabetes"
              }
            ]
          },
          {
            "name": "Index of Short Oral Discussions",
            "level": 2,
            "sessions": [
              {
                "code": "SO 068",
                "title": "Dietary diversity in practice: navigating multiple nutritional approaches"
              }
            ]
          }
        ]
      },
      {
        "name": "Late-Breaking Abstracts",
        "level": 1,
        "subsections": [
          {
            "name": "Index of LBA Oral Presentations",
            "level": 2,
            "sessions": []
          },
          {
            "name": "Index of LBA Short Oral Discussions",
            "level": 2,
            "sessions": []
          }
        ]
      }
    ]
  }
}
```

### **3. Liste Consolidée des Sessions**

Structure JSON dédiée aux sessions (pour référence rapide) :

```json
{
  "sessions": [
    {
      "code": "OP 01",
      "title": "Influencing cardiovascular outcomes: medications and behaviours",
      "section": "Abstracts",
      "subsection": "Index of Oral Presentations"
    },
    {
      "code": "OP 02",
      "title": "Novel risk factors for type 2 diabetes",
      "section": "Abstracts",
      "subsection": "Index of Oral Presentations"
    },
    {
      "code": "SO 068",
      "title": "Dietary diversity in practice: navigating multiple nutritional approaches",
      "section": "Abstracts",
      "subsection": "Index of Short Oral Discussions"
    },
    {
      "code": "OP XX",
      "title": "WITHDRAWN",
      "section": "Abstracts",
      "subsection": "Index of Oral Presentations"
    }
  ],
  "statistics": {
    "total_sessions": 150,
    "sessions_by_section": {
      "Abstracts": {
        "Index of Oral Presentations": 45,
        "Index of Short Oral Discussions": 30
      },
      "Late-Breaking Abstracts": {
        "Index of LBA Oral Presentations": 50,
        "Index of LBA Short Oral Discussions": 25
      }
    }
  }
}
```

---

## 🤖 Traitement par LLM

### **Processus**

1. **Extraction du texte** : Extraire le contenu textuel des pages 1-3 (ou plus selon la structure)

2. **Analyse par LLM** : Un modèle de langage analyse le contenu et :
   - Identifie les métadonnées dans l'en-tête
   - Extrait le titre de l'événement et les dates
   - Parse la table des matières avec sa hiérarchie
   - Identifie toutes les sessions avec leurs codes et titres
   - Détecte les sessions `WITHDRAWN`

3. **Génération du JSON** : Le LLM génère un fichier `intro_json` contenant :
   - Les métadonnées du document
   - La table des matières structurée
   - La liste consolidée des sessions avec statistiques

### **Fichier de Sortie : `intro_json`**

```json
{
  "metadata": { ... },
  "table_of_contents": { ... },
  "sessions": { ... }
}
```

---

## 📝 Notes Importantes

1. **Reconnaissance de patterns** : Cette étape repose sur la **reconnaissance de patterns** à partir du contenu textuel, pas sur des règles typographiques fixes.

2. **Référence pour le parsing** : La table des matières extraite servira de **référence** lors du parsing ultérieur des abstracts individuels.

3. **Définition de la structure** : La table des matières définit :
   - La liste des sections et leur hiérarchie
   - La liste des sessions par section (consolidée)
   - Le nombre de sessions par section
   - Les sessions marquées `WITHDRAWN`

4. **Sous-corpus** : Les pages d'introduction forment le sous-corpus `SC_introduction`, distinct de `SC_session_description`.

---

## ✅ Checklist d'Extraction

- [ ] Métadonnées du document extraites (header)
- [ ] Titre de l'événement identifié
- [ ] Lieu et dates extraits
- [ ] Table des matières parsée avec hiérarchie
- [ ] Toutes les sessions identifiées (code + titre)
- [ ] Sessions `WITHDRAWN` détectées
- [ ] Statistiques calculées (nombre de sessions par section)
- [ ] Fichier `intro_json` généré
- [ ] Éléments header/footer exclus

---

**Cette spécification définit les règles d'extraction pour les pages d'introduction du document.** 🎯

