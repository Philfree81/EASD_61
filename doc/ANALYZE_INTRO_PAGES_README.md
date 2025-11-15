# 📄 Analyse des Pages d'Introduction (SC1)

Script pour analyser les premières pages d'un PDF et extraire les métadonnées du document ainsi que la table des matières.

## 🎯 Objectif

Extraire automatiquement depuis les pages d'introduction (pages 1-3) :
- Les métadonnées du document (DOI, journal, dates, etc.)
- La table des matières structurée avec hiérarchie
- La liste consolidée des sessions avec statistiques

## 🚀 Utilisation

### **Avec LLM (recommandé)**

```bash
# Avec clé API dans l'environnement
export OPENAI_API_KEY="votre_cle_api"
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o intro_json.json

# Avec clé API en argument
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o intro_json.json \
  --api-key votre_cle_api
```

### **Sans LLM (parsing basique)**

```bash
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o intro_json.json \
  --no-llm
```

### **Pages personnalisées**

```bash
# Analyser les pages 1 à 5
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o intro_json.json \
  --start-page 1 \
  --end-page 5
```

## 📊 Format de Sortie

Le script génère un fichier JSON avec la structure suivante :

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
    "doc_title": "61st EASD Annual Meeting...",
    "event_city": "Vienna, Austria",
    "date_event_start": "2025-09-15",
    "date_event_end": "2025-09-19"
  },
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
  ],
  "statistics": {
    "total_sessions": 150,
    "sessions_by_section": {
      "Abstracts": {
        "Index of Oral Presentations": 45,
        "Index of Short Oral Discussions": 30
      }
    }
  }
}
```

## 🔧 Installation

### **Dépendances requises**

```bash
# PyMuPDF pour l'extraction PDF
pip install PyMuPDF

# OpenAI pour l'analyse LLM (optionnel mais recommandé)
pip install openai

# python-dotenv pour charger le fichier .env (optionnel mais recommandé)
pip install python-dotenv
```

### **Configuration**

Pour utiliser le LLM, vous devez avoir une clé API OpenAI :

```bash
# Option 1 : Fichier .env (recommandé)
# Créez un fichier .env à la racine du projet :
echo "OPENAI_API_KEY=sk-..." > .env
# Le script chargera automatiquement ce fichier

# Option 2 : Variable d'environnement
export OPENAI_API_KEY="sk-..."

# Option 3 : Argument --api-key
python scripts/analyze_intro_pages.py ... --api-key sk-...
```

**Note** : Le script charge automatiquement le fichier `.env` s'il existe et si `python-dotenv` est installé. Sinon, il utilise uniquement les variables d'environnement système.

## 💡 Modes d'Analyse

### **1. Mode LLM (recommandé)**

Utilise GPT-4 ou GPT-3.5-turbo pour analyser le texte et extraire les informations structurées.

**Avantages** :
- ✅ Extraction précise des métadonnées
- ✅ Reconnaissance intelligente de la structure
- ✅ Gestion des cas particuliers (WITHDRAWN, etc.)

**Inconvénients** :
- ⚠️ Nécessite une clé API OpenAI
- ⚠️ Coût par requête (minimal)
- ⚠️ Dépendance réseau

### **2. Mode Parsing Basique**

Utilise des expressions régulières pour extraire les informations.

**Avantages** :
- ✅ Pas de dépendance externe
- ✅ Gratuit
- ✅ Rapide

**Inconvénients** :
- ⚠️ Moins précis
- ⚠️ Peut manquer des cas particuliers
- ⚠️ Nécessite des ajustements pour chaque format

## 🔍 Détails d'Extraction

### **Métadonnées Extraites**

| Champ | Source | Exemple |
|-------|--------|---------|
| `tech_document_name` | En-tête | "Diabetologia (2025) 68 (Suppl 1):S1–S754" |
| `page_interne_debut` | En-tête | "S1" |
| `page_interne_fin` | En-tête | "S754" |
| `year` | En-tête | 2025 |
| `DOI_num_editeur` | URL DOI | "1007" |
| `DOI_num_doc` | URL DOI | "s00125-025-06497-1" |
| `lien_doi` | En-tête | URL complète |
| `journal` | En-tête | "Diabetologia" |
| `DOI` | URL DOI | "10.1007" |
| `nature_contenu` | En-tête | "ABSTRACTS" |
| `doc_title` | Corps | Titre de l'événement |
| `event_city` | Corps | "Vienna, Austria" |
| `date_event_start` | Corps | "2025-09-15" |
| `date_event_end` | Corps | "2025-09-19" |

### **Table des Matières**

La table des matières est structurée en 3 niveaux :

1. **Sections principales** (niveau 1)
   - `Abstracts`
   - `Late-Breaking Abstracts`

2. **Types de présentations** (niveau 2)
   - `Index of Oral Presentations`
   - `Index of Short Oral Discussions`
   - `Index of Oral Presentations` (pour LBA)
   - `Index of Short Oral Discussions` (pour LBA)

3. **Sessions individuelles** (niveau 3)
   - Format : `CODE TITRE`
   - Exemple : `OP 01 Influencing cardiovascular outcomes...`
   - Sessions LBA : `LBA OP 01`, `LBA SO 01` (dans la section "Late-Breaking Abstracts")

**Important** : Le script distingue maintenant correctement les sessions normales (`OP 01`, `SO 01`) des sessions LBA (`LBA OP 01`, `LBA SO 01`). Les sessions LBA sont placées dans la section "Late-Breaking Abstracts".

### **Sessions WITHDRAWN**

Les sessions marquées `WITHDRAWN` sont détectées et leur titre est remplacé par `"WITHDRAWN"`.

## 🐛 Troubleshooting

### **Erreur : "OpenAI non disponible"**

**Solution** :
```bash
pip install openai
```

Ou utilisez le mode parsing basique :
```bash
python scripts/analyze_intro_pages.py ... --no-llm
```

### **Erreur : "PyMuPDF requis"**

**Solution** :
```bash
pip install PyMuPDF
```

### **Erreur : "API key not found"**

**Solution** :
```bash
# Définir la variable d'environnement
export OPENAI_API_KEY="sk-..."

# Ou passer en argument
python scripts/analyze_intro_pages.py ... --api-key sk-...
```

### **Extraction incomplète**

Si certaines métadonnées manquent :

1. **Vérifier les pages** : Les informations peuvent être sur d'autres pages
   ```bash
   python scripts/analyze_intro_pages.py ... --end-page 5
   ```

2. **Utiliser le LLM** : Le parsing basique peut être incomplet
   ```bash
   # Retirer --no-llm pour utiliser le LLM
   ```

3. **Vérifier le format** : Le PDF peut avoir un format différent

## 📝 Exemples d'Utilisation

### **Exemple 1 : Extraction complète**

```bash
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o intro_json.json
```

### **Exemple 2 : Parsing basique uniquement**

```bash
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o intro_json_basic.json \
  --no-llm
```

### **Exemple 3 : Pages personnalisées**

```bash
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o intro_json.json \
  --start-page 1 \
  --end-page 4
```

## 🔄 Intégration dans le Pipeline

```bash
# 1. Analyser les pages d'introduction
python scripts/analyze_intro_pages.py \
  -i data/s00125-025-06497-1.pdf \
  -o intro_json.json

# 2. Extraire le contenu neutre
python scripts/neutral_extractor.py \
  -i data/s00125-025-06497-1.pdf \
  -o neutral.json

# 3. Typage sémantique (pass 1, 2, 3)
# ...

# 4. Utiliser intro_json.json comme référence
# pour valider et enrichir les abstracts
```

## ✅ Checklist

- [ ] PyMuPDF installé
- [ ] OpenAI installé (si utilisation LLM)
- [ ] python-dotenv installé (recommandé pour .env)
- [ ] Clé API configurée dans `.env` ou variable d'environnement (si utilisation LLM)
- [ ] PDF accessible
- [ ] Fichier JSON généré
- [ ] Métadonnées complètes
- [ ] Table des matières structurée
- [ ] Sessions listées (y compris LBA si présentes)

---

**Ce script est la première étape du pipeline d'extraction, fournissant les métadonnées et la structure du document.** 🎯

