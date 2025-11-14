# 📚 Documentation Neutral Extractor - Index

## 🎯 Démarrage rapide

**Vous êtes nouveau ?** Commencez ici :

1. 📖 [**GETTING_STARTED.md**](GETTING_STARTED.md) - Tutoriel pas-à-pas (15 min)
2. 📋 [**QUICK_REFERENCE.md**](QUICK_REFERENCE.md) - Référence rapide (5 min)

---

## 📖 Documentation complète

### Pour comprendre le système

| Document | Description | Temps de lecture |
|----------|-------------|------------------|
| [**README_NEUTRAL_EXTRACTOR.md**](README_NEUTRAL_EXTRACTOR.md) | Documentation exhaustive | 30-45 min |
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | Vision globale du pipeline | 15 min |
| [**CHANGELOG_v1.3.md**](CHANGELOG_v1.3.md) | Historique des versions | 10 min |

---

## 🔧 Scripts et outils

| Fichier | Description | Usage |
|---------|-------------|-------|
| `neutral_extractor.py` | **Script principal d'extraction** | CLI ou import Python |
| `example_usage.py` | Exemples d'utilisation et analyses | `python example_usage.py output.json` |

---

## 📂 Structure par besoin

### Je veux...

#### ...démarrer rapidement
1. ➡️ [GETTING_STARTED.md](GETTING_STARTED.md)
2. Lancer : `python neutral_extractor.py -i doc.pdf -o out.json`
3. ✓ Fait !

---

#### ...comprendre ce que fait le script
1. ➡️ [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (concepts de base)
2. ➡️ [README - Section "Fonctionnalités"](README_NEUTRAL_EXTRACTOR.md#-fonctionnalités)
3. ➡️ [ARCHITECTURE.md - Section "Couche Neutre"](ARCHITECTURE.md#couche-1--neutre-)

---

#### ...utiliser le script dans mon code Python
1. ➡️ [README - Section "Utilisation programmatique"](README_NEUTRAL_EXTRACTOR.md#utilisation-programmatique)
2. ➡️ Voir `example_usage.py` pour des exemples concrets

```python
from neutral_extractor import NeutralExtractor

extractor = NeutralExtractor()
data = extractor.extract_from_pdf("doc.pdf")
extractor.save_to_json(data, "output.json")
```

---

#### ...comprendre la structure JSON
1. ➡️ [README - Section "Structure des données"](README_NEUTRAL_EXTRACTOR.md#-structure-des-données)
2. ➡️ [QUICK_REFERENCE - Section "Structure JSON"](QUICK_REFERENCE.md#-structure-json-simplifié)

**En bref :**
```json
{
  "metadata": { ... },
  "signature_catalog": { ... },
  "elements": [ ... ]
}
```

---

#### ...analyser un nouveau type de PDF
1. ➡️ [GETTING_STARTED - Tutoriel médical](GETTING_STARTED.md#-tutoriel--analyser-un-pdf-médical)
2. Extraire → Analyser catalogue → Documenter signatures
3. ➡️ Préparer pour [couche sémantique](ARCHITECTURE.md#couche-2--sémantique-)

---

#### ...personnaliser l'extraction
1. ➡️ [README - Section "Paramètres techniques"](README_NEUTRAL_EXTRACTOR.md#-paramètres-techniques)
2. Options CLI : `--y-tolerance`, `--no-merge`
3. Modification code : `X_THRESHOLD`, critères de fusion

---

#### ...résoudre un problème
1. ➡️ [README - Section "Dépannage"](README_NEUTRAL_EXTRACTOR.md#-dépannage)
2. ➡️ [GETTING_STARTED - Section "Dépannage"](GETTING_STARTED.md#-dépannage)
3. Vérifier les logs du script

---

#### ...comprendre l'architecture globale
1. ➡️ [ARCHITECTURE.md](ARCHITECTURE.md) (vue d'ensemble complète)
2. ➡️ [README - Section "Architecture technique"](README_NEUTRAL_EXTRACTOR.md#%EF%B8%8F-architecture-technique)

**En bref :**
```
PDF → Couche Neutre → Couche Sémantique → Données structurées
         (maintenant)      (à venir)
```

---

#### ...préparer la couche sémantique
1. ➡️ [ARCHITECTURE - Section "Prochaines étapes"](ARCHITECTURE.md#-prochaines-étapes)
2. ➡️ [README - Section "Évolution future"](README_NEUTRAL_EXTRACTOR.md#-évolution-future)
3. Documenter signatures → Créer rules.yaml

---

## 🗂️ Carte de la documentation

```
Documentation/
│
├── 🚀 POUR DÉMARRER
│   ├── GETTING_STARTED.md          ← Commencer ici !
│   └── QUICK_REFERENCE.md          ← Aide-mémoire
│
├── 📖 POUR COMPRENDRE
│   ├── README_NEUTRAL_EXTRACTOR.md ← Documentation complète
│   ├── ARCHITECTURE.md             ← Vision système
│   └── CHANGELOG_v1.3.md           ← Nouveautés
│
├── 💻 POUR UTILISER
│   ├── neutral_extractor.py        ← Script principal
│   └── example_usage.py            ← Exemples
│
└── 📑 NAVIGATION
    └── INDEX.md                    ← Vous êtes ici
```

---

## 📊 Documentation par niveau

### 🟢 Débutant
Vous découvrez le projet :
1. [GETTING_STARTED.md](GETTING_STARTED.md) - Premier pas
2. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Syntaxe de base

### 🟡 Intermédiaire
Vous utilisez régulièrement :
1. [README - Cas d'usage](README_NEUTRAL_EXTRACTOR.md#-cas-dusage)
2. [README - Paramètres](README_NEUTRAL_EXTRACTOR.md#-paramètres-techniques)
3. `example_usage.py` - Techniques avancées

### 🔴 Avancé
Vous étendez/modifiez le système :
1. [README - Architecture technique](README_NEUTRAL_EXTRACTOR.md#%EF%B8%8F-architecture-technique)
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Design complet
3. Code source commenté

---

## 🎓 Parcours d'apprentissage suggéré

### Jour 1 : Découverte (2h)
```
1. GETTING_STARTED.md (installation + première extraction)
2. QUICK_REFERENCE.md (concepts clés)
3. Premier test sur votre PDF
```

### Jour 2 : Exploration (3h)
```
1. README - Sections "Fonctionnalités" et "Structure"
2. Analyser plusieurs PDFs du même type
3. Documenter les signatures communes
```

### Jour 3 : Maîtrise (4h)
```
1. README - Section "Cas d'usage"
2. example_usage.py (reproduire les exemples)
3. ARCHITECTURE.md (comprendre la vision)
```

### Semaine 2 : Préparation sémantique
```
1. README - Section "Évolution future"
2. ARCHITECTURE - "Prochaines étapes"
3. Créer les règles YAML pour vos PDFs
```

---

## 🔍 Recherche rapide

### Par concept

| Concept | Où le trouver |
|---------|---------------|
| Signatures typographiques | [README](README_NEUTRAL_EXTRACTOR.md#2-signatures-typographiques) |
| Métadonnées de ligne | [README](README_NEUTRAL_EXTRACTOR.md#3-métadonnées-de-ligne) |
| Images | [README](README_NEUTRAL_EXTRACTOR.md#1-extraction-exhaustive) |
| Tables | [README](README_NEUTRAL_EXTRACTOR.md#1-extraction-exhaustive) |
| Exposants | [README](README_NEUTRAL_EXTRACTOR.md#4-rattachement-des-exposants) |
| Ordre de lecture | [QUICK_REF](QUICK_REFERENCE.md#-système-de-lignes) |
| Structure JSON | [README](README_NEUTRAL_EXTRACTOR.md#-structure-des-données) |
| Paramètres | [README](README_NEUTRAL_EXTRACTOR.md#-paramètres-techniques) |

### Par tâche

| Tâche | Où le trouver |
|-------|---------------|
| Installer | [GETTING_STARTED](GETTING_STARTED.md#-prérequis) |
| Extraire un PDF | [GETTING_STARTED](GETTING_STARTED.md#étape-2--première-extraction) |
| Analyser les signatures | [GETTING_STARTED](GETTING_STARTED.md#étape-2--analyser-le-catalogue-de-signatures) |
| Filtrer par type | [QUICK_REF](QUICK_REFERENCE.md#-filtres-courants) |
| Reconstruire texte | [README](README_NEUTRAL_EXTRACTOR.md#3-extraction-par-zone) |
| Exporter images | [GETTING_STARTED](GETTING_STARTED.md#cas-2--extraire-uniquement-les-images) |
| Déboguer | [README](README_NEUTRAL_EXTRACTOR.md#-dépannage) |

---

## 📞 FAQ rapide

**Q : Par où commencer ?**  
→ [GETTING_STARTED.md](GETTING_STARTED.md)

**Q : Comment ça marche en 1 phrase ?**  
→ Extrait tout du PDF sans interpréter, annote avec signatures typo

**Q : C'est quoi une signature ?**  
→ `"FontName_Size_Flags"` ex: `"Arial-Bold_12.0_20"`

**Q : Pourquoi "neutre" ?**  
→ Pas d'interprétation sémantique, réutilisable pour tout PDF

**Q : Et la couche sémantique ?**  
→ À venir ! Voir [ARCHITECTURE.md](ARCHITECTURE.md)

**Q : Ça gère les tables ?**  
→ Oui, mais si converties en images, extraites comme images

**Q : Les images où ?**  
→ Dossier `{nom_fichier}_images/`

**Q : JSON trop gros ?**  
→ Normal, contient tout. Filtrer programmatiquement

**Q : Modifier le seuil de colonnes ?**  
→ `X_THRESHOLD = 305` dans le code

**Q : Personnaliser ?**  
→ Voir [README - Paramètres](README_NEUTRAL_EXTRACTOR.md#-paramètres-techniques)

---

## 🎯 Checklist complète

### Installation
- [ ] Python 3.7+ installé
- [ ] PyMuPDF installé
- [ ] Script téléchargé
- [ ] Premier test réussi

### Compréhension
- [ ] GETTING_STARTED.md lu
- [ ] Concept de "neutralité" compris
- [ ] Structure JSON comprise
- [ ] Signatures typographiques comprises

### Utilisation
- [ ] Premier PDF extrait
- [ ] JSON analysé
- [ ] Signatures documentées
- [ ] Images extraites (si présentes)

### Maîtrise
- [ ] Cas d'usage explorés
- [ ] example_usage.py testé
- [ ] Filtres maîtrisés
- [ ] Paramètres ajustés si besoin

### Préparation suite
- [ ] ARCHITECTURE.md lu
- [ ] Patterns de PDFs identifiés
- [ ] Règles YAML esquissées
- [ ] Prêt pour couche sémantique

---

## 🌟 Ressources externes

### PyMuPDF
- 📚 [Documentation officielle](https://pymupdf.readthedocs.io/)
- 🎓 [Tutoriels](https://pymupdf.readthedocs.io/en/latest/tutorial.html)
- 💬 [Forum](https://github.com/pymupdf/PyMuPDF/discussions)

### Python
- 🐍 [Python.org](https://www.python.org/)
- 📖 [JSON en Python](https://docs.python.org/3/library/json.html)
- 🎯 [Pathlib](https://docs.python.org/3/library/pathlib.html)

---

## ✅ Validation de compréhension

Vous avez bien compris si vous pouvez :

1. [ ] Expliquer la différence entre couche neutre et sémantique
2. [ ] Extraire un PDF et analyser le JSON produit
3. [ ] Identifier les signatures dans le catalogue
4. [ ] Filtrer les éléments par type, page, ou signature
5. [ ] Reconstruire l'ordre de lecture d'un document
6. [ ] Expliquer à quoi serviront les signatures dans la couche sémantique

---

## 🚀 Prochaine étape

**Vous maîtrisez la couche neutre ?**

➡️ **Passez à la couche sémantique !**

1. Créer `rules.yaml` avec vos mappings
2. Développer `semantic_extractor.py`
3. Produire des données structurées

Voir [ARCHITECTURE.md - Prochaines étapes](ARCHITECTURE.md#-prochaines-étapes)

---

**📧 Questions ? Consultez d'abord [README - Dépannage](README_NEUTRAL_EXTRACTOR.md#-dépannage)**

---

*Dernière mise à jour : Novembre 2024*  
*Version : 1.3*
