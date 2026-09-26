# Changelog

Toutes les modifications notables de ce projet sont documentées ici.
Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

## [Non publié]

## [2.5.0] - 2026-09-26

### Sécurité
- **Sanitization active par défaut** : le HTML de sortie est nettoyé automatiquement
  (CLI, `EmlToHtmlConverter` et `batch_convert`), sans besoin du flag `--sanitize` —
  ouvrir le HTML d'un email non fiable n'exécute plus ses scripts. Nouveau flag
  `--no-sanitize` pour la désactiver sur des sources de confiance ; l'ancien flag
  `--sanitize` reste accepté (no-op) pour ne pas casser les scripts existants
- `--extract-attachments` : les pièces jointes aux extensions actives
  (`.html`, `.htm`, `.xhtml`, `.svg`, `.xml`, `.mht`, `.mhtml`) sont renommées avec un
  suffixe `.txt` pour éviter l'exécution de leur contenu à l'ouverture ; le lien de
  téléchargement pointe vers le fichier renommé

### Corrigé
- La balise `<meta charset>` est désormais injectée même quand le HTML de l'email n'a
  pas de balise `<head>` (création d'un `<head>` après `<html>`, ou préfixage du
  contenu si `<html>` est absent) — corrige les mojibake à l'affichage

## [2.4.0] - 2026-09-23

### Ajouté
- Publication PyPI sous le nom `eml2html` (`eml-to-html` était déjà pris sur PyPI) :
  `pip install eml2html`
- Commande `eml2html` ; l'alias `eml-to-html` reste installé
- Workflow GitHub Actions `publish.yml` : tests + build + publication automatique
## [2.3.0] - Fusionné

### Ajouté
- Bloc d'en-têtes en haut du HTML généré : De, À, Cc, Cci (si présent), Date, Objet,
  avec décodage des MIME encoded-words et échappement HTML (issue #6)
- Mode batch récursif : flag `-r`/`--recursive`, arborescence recréée en sortie
- Paquet pip-installable : métadonnées PEP 621 dans `pyproject.toml`,
  commande console, zéro dépendance conservée
- Gestion des pièces jointes non-image : listées en pied du HTML généré (nom, type, taille) ;
  flag `--extract-attachments` avec nettoyage des noms (traversée neutralisée, doublons suffixés)

### Ajouté
- Bloc d'en-têtes en haut du HTML généré : De, À, Cc, Cci (si présent), Date, Objet,
  avec décodage des MIME encoded-words (accents, noms non-ASCII) et échappement HTML
- Mode batch récursif : flag `-r`/`--recursive` (et `batch_convert(recursive=True)`),
  parcours des sous-dossiers avec recréation de l'arborescence dans la sortie
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