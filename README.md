# Convertisseur EML en HTML

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-success)](#-prérequis)
[![PyPI](https://img.shields.io/pypi/v/eml2html.svg)](https://pypi.org/project/eml2html/)
[![CI](https://github.com/Baebibelab/eml_to_html/actions/workflows/ci.yml/badge.svg)](https://github.com/Baebibelab/eml_to_html/actions/workflows/ci.yml)
![Status](https://img.shields.io/badge/status-active-success.svg)

Outil Python pour convertir des fichiers `.eml` (emails exportés) en fichiers `.html` autonomes, avec les images inline encodées en base64 directement dans le HTML.

## ✨ Fonctionnalités

- 🔄 Conversion d'un fichier `.eml` unique ou d'un dossier entier (mode batch)
- 🖼️ Extraction et intégration automatique des images inline (`cid:`) en base64
- 🔤 Détection et correction automatique de l'encodage de caractères (UTF-8, ISO-8859-1, etc.)
- 🏷️ Correction de la balise `<meta charset>` pour un affichage correct dans le navigateur
- 📁 Traitement par lot avec gestion d'erreurs isolée (un échec n'interrompt pas le reste)
- 🖥️ Interface en ligne de commande (CLI) simple, avec codes de sortie exploitables (0 = succès, 1 = échec)
- 📝 Les emails sans partie HTML (texte brut) sont convertis en HTML valide avec échappement
- 🏷️ Correction du `<meta charset>` pour les formes HTML4 (`http-equiv`) et HTML5 (`charset=`)
- ✅ Suite de tests (`pytest`) et intégration continue (lint `ruff` + tests sur Python 3.9–3.13)
- 🛡️ Sanitization **active par défaut** : les éléments actifs du HTML (scripts, handlers d'événements,
  iframes, formulaires, meta refresh, URI `javascript:`) sont retirés automatiquement — sans aucune
  dépendance externe ; `--no-sanitize` permet de la désactiver
- 📎 Les pièces jointes non-image sont listées en pied du HTML (nom, type, taille) ;
  `--extract-attachments` les sauvegarde dans un dossier dédié avec liens de téléchargement
- 📧 Les en-têtes de l'email (De, À, Cc, Cci, Date, Objet) sont affichés en haut du HTML
  généré, avec décodage des accents et noms encodés (MIME encoded-words)

## 📦 Prérequis

- Python 3.8 ou supérieur
- Aucune dépendance externe pour l'outil (uniquement la bibliothèque standard Python)
- `pytest` uniquement pour exécuter les tests (`pip install pytest`)

## 🚀 Installation

### Depuis PyPI (recommandé)

```bash
pip install eml2html
```

Les commandes `eml2html` et `eml-to-html` (alias) sont ensuite disponibles
depuis n'importe quel dossier :

```bash
eml2html chemin/vers/email.eml
```

Mise à jour : `pip install --upgrade eml2html`

### Depuis GitHub (version de développement)

```bash
pip install git+https://github.com/Baebibelab/eml_to_html.git
```

### Sans installation (script autonome)

```bash
git clone https://github.com/Baebibelab/eml_to_html.git
cd eml_to_html
python eml_to_html.py chemin/vers/email.eml
```

Aucune dépendance externe n'est requise dans les deux cas.

## 🛠️ Utilisation

### Convertir un seul fichier

```bash
python eml_to_html.py chemin/vers/email.eml
```

Le fichier HTML est créé automatiquement à côté, avec le même nom (`email.html`).

### Spécifier un fichier de sortie

```bash
python eml_to_html.py email.eml -o sortie.html
```

### Convertir un dossier entier (mode batch)

```bash
python eml_to_html.py chemin/vers/dossier/
```

### Spécifier un dossier de sortie

```bash
python eml_to_html.py chemin/vers/dossier/ -o chemin/vers/sortie/
```

### Parcourir les sous-dossiers (mode récursif)

```bash
python eml_to_html.py chemin/vers/dossier/ --recursive
```

Sans `--recursive`, seuls les `.eml` directement dans le dossier sont convertis.
Avec, toute l'arborescence est parcourue et **recréée telle quelle** dans la sortie
(`archives/2023/email.eml` → `archives/2023/email.html`).

### Afficher l'aide

```bash
python eml_to_html.py -h
```

### Sanitization du HTML de sortie (active par défaut)

```bash
python eml_to_html.py email.eml                # sanitization active
python eml_to_html.py email.eml --no-sanitize   # la désactiver
```

La sanitization est **active par défaut** (CLI, `EmlToHtmlConverter` et `batch_convert`) :
le HTML de l'email est nettoyé avant l'écriture (liste blanche de balises et d'attributs,
implémentation stdlib pure), pour que l'ouverture dans un navigateur n'exécute pas les
scripts qu'il contient. Utilisez `--no-sanitize` uniquement pour des sources de confiance :

| Retiré | Conservé |
|---|---|
| `<script>`, `<iframe>`, `<object>`, `<embed>`, `<form>`, `<link>` | Mise en page, tableaux, styles inoffensifs |
| Attributs `on...` (`onclick`, `onerror`, ...) | Images inline en base64 (`data:image/...`) |
| URI `javascript:`, `vbscript:`, data URIs hors liste blanche (`data:image/svg+xml`,
  `data:text/html`), URL dangereuse dans `srcset` | Liens `http(s):`, `mailto:`,
  images inline `data:image/png|jpeg|gif|bmp|webp` |
| `<meta http-equiv="refresh">`, CSS `expression()` | Balise `<meta charset>` corrigée |

Le texte visible est toujours préservé. Recommandé pour tout email de source non fiable.

### Pièces jointes

Les pièces jointes non-image (PDF, DOCX, ...) sont automatiquement listées en pied du HTML
généré : nom, type MIME et taille.

```bash
python eml_to_html.py email.eml --extract-attachments
```

Avec `--extract-attachments`, elles sont en plus sauvegardées dans un dossier
`<nom-du-html>_pieces-jointes/` à côté du fichier HTML, et la section en pied de page
contient un lien de téléchargement vers chaque fichier. Les noms de fichiers sont nettoyés
(traversée de chemin neutralisée, doublons suffixés `-2`, `-3`...).

### Codes de sortie

- `0` : toutes les conversions ont réussi
- `1` : le chemin n'existe pas, ou au moins une conversion a échoué (utile en script/CI)

### Utiliser comme bibliothèque (paquet installé)

```python
from eml_to_html import EmlToHtmlConverter, batch_convert

html = EmlToHtmlConverter('email.eml').save('sortie.html')
succeeded, failed = batch_convert('dossier/')
```

## 📋 Options

| Option | Description |
|---|---|
| `path` | Chemin d'un fichier `.eml` ou d'un dossier (obligatoire) |
| `-o`, `--output` | Fichier ou dossier de sortie (optionnel) |
| `--no-sanitize` | Désactive la sanitization du HTML de sortie — active par défaut |
| `--sanitize` | Obsolète (no-op) : la sanitization est désormais active par défaut |
| `--extract-attachments` | Sauvegarde les pièces jointes non-image dans un dossier dédié |
| `-r`, `--recursive` | Parcourt aussi les sous-dossiers (arborescence recréée en sortie) |
| `-h`, `--help` | Affiche l'aide |

## 🧩 Structure du projet

```
eml_to_html/
├── eml_to_html.py       # Script principal
├── tests/               # Suite de tests pytest
├── examples/           # Emails de démo pour test manuel (voir examples/README.md)
├── .github/workflows/   # CI (ruff + pytest)
├── pyproject.toml       # Configuration ruff / pytest
├── README.md            # Documentation
├── LICENSE              # Licence du projet
├── CHANGELOG.md         # Historique des versions
└── .gitignore           # Fichiers ignorés par Git
```

## 🧪 Tester avec des emails de démo

Le dossier [`examples/`](examples/) contient trois emails **synthétiques et inoffensifs**
pour tester l'outil en conditions réelles avant d'utiliser vos propres emails :
sanitization, charset sans `<head>`, pièces jointes actives. Chaque démo a sa
checklist de points de contrôle — voir [`examples/README.md`](examples/README.md).

## ⚙️ Fonctionnement technique

1. Le fichier `.eml` est chargé via le module `email` de la bibliothèque standard.
2. Les en-têtes principaux (De, À, Cc, Cci, Date, Objet) sont décodés ( MIME encoded-words)
   et affichés dans un bloc en haut du HTML généré.
2. Le corps HTML (ou texte brut en fallback) est extrait et décodé selon le charset déclaré.
3. La balise `<meta charset>` est corrigée pour correspondre à l'encodage réel (UTF-8).
4. Les pièces jointes de type image sont parcourues et converties en `data:image/...;base64,...`, puis injectées dans le HTML en remplaçant les références `cid:` ou noms de fichiers.
5. Le résultat est un fichier `.html` autonome, lisible sans dépendance externe (pas besoin des pièces jointes séparées).

## 🐛 Limitations connues

- Seuls les formats d'image suivants sont supportés : JPEG, PNG, GIF, BMP, WEBP
- Les pièces jointes non-image sont listées en pied de page (et extraites avec `--extract-attachments`),
  mais leur contenu n'est pas intégré au HTML
- Le HTML généré est sanitizé par défaut ; avec `--no-sanitize` il ne l'est pas (à ouvrir avec
  prudence si la source n'est pas fiable)
- Avec `--extract-attachments`, les pièces jointes aux extensions actives (`.html`, `.svg`,
  `.xml`, `.mht`, ...) sont renommées avec un suffixe `.txt` pour éviter l'exécution de leur
  contenu à l'ouverture
- Sans `--recursive`, le mode batch ne traverse pas les sous-dossiers

## 📄 Licence

Ce projet est distribué sous licence [MIT](LICENSE)

## 🔒 Confidentialité et sécurité

⚠️ **Attention** : cet outil traite des fichiers email pouvant contenir des données personnelles ou confidentielles.
- Aucune donnée n'est envoyée en ligne : tout le traitement est **local**.
- Ne commitez jamais de vrais fichiers `.eml` contenant des informations sensibles dans ce dépôt (voir `.gitignore`).
- Le HTML généré est sanitizé par défaut : les scripts embarqués dans des emails non fiables sont neutralisés. Ne désactivez la sanitization (`--no-sanitize`) que pour des sources de confiance.

## 🌟 Star History

Si cet outil vous est utile, n'hésitez pas à mettre une ⭐ au dépôt !

## 📬 Contact

Pour toute question, ouvrez une [issue](../../issues) sur ce dépôt.

## 👤 Auteur

Développé par Romain BEAL
