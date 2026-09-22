# Changelog

Toutes les modifications notables de ce projet sont documentées ici.
Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

## [2.3.0] - Non publié

### Ajouté
- Paquet pip-installable : métadonnées PEP 621 dans `pyproject.toml`, commande `eml-to-html` (point d'entrée console), zéro dépendance conservée
- Gestion des pièces jointes non-image : listées en pied du HTML généré (nom, type MIME, taille)
- Flag `--extract-attachments` : sauvegarde les pièces jointes dans un dossier `<html>_pieces-jointes/`
  avec nettoyage des noms de fichiers (traversée de chemin neutralisée, doublons suffixés)
- Option `--sanitize` (CLI, `EmlToHtmlConverter(sanitize=True)` et `batch_convert(sanitize=True)`) :
  retire les scripts, handlers d'événements, iframes, formulaires, meta refresh et URI `javascript:`
  du HTML de sortie via une liste blanche stdlib pure (`html.parser.HTMLParser`)
- Suite de tests `pytest` (20 tests) couvrant le décodage, les images inline, le mode batch et les codes de sortie
- CI GitHub Actions : lint `ruff` + tests sur Python 3.9, 3.11 et 3.13
- Configuration `pyproject.toml` (ruff, pytest)
- Les emails sans partie HTML (texte brut) sont désormais convertis en document HTML valide (échappement + `<br>`)
- `batch_convert` retourne un tuple `(réussis, échecs)` et la CLI sort avec un code d'erreur non nul en cas d'échec
- Support de la forme HTML5 `<meta charset="...">` (en plus de la forme `http-equiv`)
- Détection insensible à la casse des extensions `.eml` en mode batch

### Modifié
- Le module ne configure plus le logging global à l'import (`logging.basicConfig` déplacé dans `main()`) : utilisable comme bibliothèque
- Le remplacement des images par nom de fichier ne cible plus que les attributs `src`/`background`/`data-src` (évite de corrompre le texte ou les liens)

### Supprimé
- Import `os` inutilisé

## [2.0.0] - 2026-09-22

### Ajouté
- Interface en ligne de commande (CLI) via `argparse`
- Mode de traitement par lot (`batch_convert`) pour convertir un dossier entier
- Gestion d'erreurs isolée par fichier en mode batch
- Support des formats d'image WEBP et BMP
- Logging structuré (remplace les `print`)

### Modifié
- Refactorisation complète en classe `EmlToHtmlConverter` (meilleure séparation des responsabilités)
- **Fix** : priorité de décodage corrigée — le charset déclaré dans l'email est désormais testé avant l'UTF-8 par défaut, évitant un décodage silencieusement erroné

### Supprimé
- Saisie interactive via `input()` (remplacée par les arguments CLI)

## [1.0.0] - Date initiale

### Ajouté
- Conversion basique d'un fichier `.eml` en `.html`
- Extraction des images inline en base64
- Correction de la balise `<meta charset>`
- Saisie interactive du chemin du fichier