# Changelog

Toutes les modifications notables de ce projet sont documentées ici.
Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

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