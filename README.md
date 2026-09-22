# Convertisseur EML en HTML

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-success)](requirements.txt)

Outil Python pour convertir des fichiers `.eml` (emails exportés) en fichiers `.html` autonomes, avec les images inline encodées en base64 directement dans le HTML.

## ✨ Fonctionnalités

- 🔄 Conversion d'un fichier `.eml` unique ou d'un dossier entier (mode batch)
- 🖼️ Extraction et intégration automatique des images inline (`cid:`) en base64
- 🔤 Détection et correction automatique de l'encodage de caractères (UTF-8, ISO-8859-1, etc.)
- 🏷️ Correction de la balise `<meta charset>` pour un affichage correct dans le navigateur
- 📁 Traitement par lot avec gestion d'erreurs isolée (un échec n'interrompt pas le reste)
- 🖥️ Interface en ligne de commande (CLI) simple

## 📦 Prérequis

- Python 3.8 ou supérieur
- Aucune dépendance externe (uniquement la bibliothèque standard Python)

## 🚀 Installation

```bash
git clone https://github.com/Baebibelab/eml_to_html.git
cd eml_to_html
```

Aucune installation de package n'est nécessaire.

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

### Afficher l'aide

```bash
python eml_to_html.py -h
```

## 📋 Options

| Option | Description |
|---|---|
| `path` | Chemin d'un fichier `.eml` ou d'un dossier (obligatoire) |
| `-o`, `--output` | Fichier ou dossier de sortie (optionnel) |
| `-h`, `--help` | Affiche l'aide |

## 🧩 Structure du projet

```
eml_to_html/
├── eml_to_html.py       # Script principal
├── README.md            # Documentation
├── LICENSE              # Licence du projet
├── CHANGELOG.md         # Historique des versions
└── .gitignore           # Fichiers ignorés par Git
```

## ⚙️ Fonctionnement technique

1. Le fichier `.eml` est chargé via le module `email` de la bibliothèque standard.
2. Le corps HTML (ou texte brut en fallback) est extrait et décodé selon le charset déclaré.
3. La balise `<meta charset>` est corrigée pour correspondre à l'encodage réel (UTF-8).
4. Les pièces jointes de type image sont parcourues et converties en `data:image/...;base64,...`, puis injectées dans le HTML en remplaçant les références `cid:` ou noms de fichiers.
5. Le résultat est un fichier `.html` autonome, lisible sans dépendance externe (pas besoin des pièces jointes séparées).

## 🐛 Limitations connues

- Seuls les formats d'image suivants sont supportés : JPEG, PNG, GIF, BMP, WEBP
- Les pièces jointes non-image (PDF, DOCX, etc.) ne sont pas traitées
- Le HTML généré n'est pas sanitizé (à utiliser avec précaution sur des emails de sources non fiables)

## 📄 Licence

Ce projet est distribué sous licence [MIT](LICENSE)

## 🔒 Confidentialité et sécurité

⚠️ **Attention** : cet outil traite des fichiers email pouvant contenir des données personnelles ou confidentielles.
- Aucune donnée n'est envoyée en ligne : tout le traitement est **local**.
- Ne commitez jamais de vrais fichiers `.eml` contenant des informations sensibles dans ce dépôt (voir `.gitignore`).
- Le HTML généré n'est pas sanitizé : si vous l'ouvrez dans un navigateur, méfiez-vous des scripts embarqués dans des emails provenant de sources non fiables.

## 🌟 Star History

Si cet outil vous est utile, n'hésitez pas à mettre une ⭐ au dépôt !

## 📬 Contact

Pour toute question, ouvrez une [issue](../../issues) sur ce dépôt.

## 👤 Auteur

Développé par Romain BEAL
