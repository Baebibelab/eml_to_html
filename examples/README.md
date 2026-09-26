# Emails de démonstration

Trois emails **synthétiques et inoffensifs** pour tester `eml2html` en conditions réelles,
sans risquer ses propres emails. Aucune donnée personnelle, tout est fictif.

## Principe

Chaque fichier met en scène une nouveauté récente. La commande produit un `.html`
que vous ouvrez dans un navigateur : le comportement attendu est décrit point par point.

```bash
# Depuis la racine du dépôt (ou avec `pip install eml2html` installé)
python eml_to_html.py examples/demo-sanitization.eml -o /tmp/test1.html
```

---

## Démo 1 — Sanitization : `demo-sanitization.eml`

Cet email contient l'arsenal classique d'un email malveillant : script inline, handler
`onclick`, lien `javascript:`, image avec `onerror`, data URI SVG piégé, `srcset` avec
une URL dangereuse, CSS `expression()`, iframe, formulaire.

```bash
python eml_to_html.py examples/demo-sanitization.eml -o /tmp/test1.html
```

Ouvrez `/tmp/test1.html` dans un navigateur, **sans `--no-sanitize`** :

| Point de contrôle | Attendu |
|---|---|
| Aucune alerte JavaScript ne se déclenche à l'ouverture | ✅ |
| Le texte « Texte legitime contenant javascript: void 0 (doit rester intact). » est affiché tel quel | ✅ |
| Le lien « lien normal » reste cliquable (https://example.com) | ✅ |
| Le lien « lien javascript » est neutralisé (texte sans href actif) | ✅ |
| Le style `p > span { color: red }` est appliqué si vous ajoutez un `<span>` — le sélecteur n'est pas corrompu | ✅ |
| Aucune iframe, aucun formulaire visible | ✅ |

Comparez ensuite avec la version non nettoyée (**à vos risques et périls, dans un
navigateur jetable**) :

```bash
python eml_to_html.py examples/demo-sanitization.eml -o /tmp/test1-brut.html --no-sanitize
```

Le HTML brut contient bien les scripts : c'est la démonstration de ce que le défaut
« sanitization active » neutralise désormais automatiquement.

---

## Démo 2 — Charset sans `<head>` : `demo-charset-nohead.eml`

Cet email est encodé en **ISO-8859-1** et son HTML n'a **pas de balise `<head>`** —
un cas très fréquent dans les emails réels. Avant la correction, le meta charset
n'était jamais injecté et les accents s'affichaient mal (mojibake).

```bash
python eml_to_html.py examples/demo-charset-nohead.eml -o /tmp/test2.html
```

| Point de contrôle | Attendu |
|---|---|
| Le texte « é è ê ç à ù ... » s'affiche avec les accents corrects, sans caractères bizarres (Ã©, Ã¨...) | ✅ |
| Le fichier contient `<meta ... charset=UTF-8>` (visible via Ctrl+U / voir la source) | ✅ |

---

## Démo 3 — Pièces jointes actives : `demo-pieces-jointes.eml`

Cet email a deux pièces jointes : `page.html` (contient un script — **active**) et
`rapport.pdf` (inoffensif).

```bash
python eml_to_html.py examples/demo-pieces-jointes.eml -o /tmp/test3.html --extract-attachments
```

| Point de contrôle | Attendu |
|---|---|
| La section « Pièces jointes » en pied de page liste les deux fichiers | ✅ |
| Sur le disque, le dossier `/tmp/test3_pieces-jointes/` contient `page.html.txt` (suffixe `.txt` ajouté) et `rapport.pdf` (nom inchangé) | ✅ |
| Le lien de téléchargement pointe vers `page.html.txt` | ✅ |
| Ouvrir `page.html.txt` dans un navigateur affiche le code source, n'exécute pas le script | ✅ |

---

## Tester avec vos propres emails

Une fois les démos validées, le flux est identique sur vos archives :

```bash
# Dossier complet d'exports
python eml_to_html.py chemin/vers/exports/ -o chemin/vers/sortie/ --recursive

# Un email précis, avec extraction des pièces jointes
python eml_to_html.py chemin/vers/email.eml --extract-attachments
```

La sanitization est active par défaut ; ajoutez `--no-sanitize` uniquement pour des
sources de confiance.

## En cas de comportement inattendu

Ouvrez une issue sur https://github.com/Baebibelab/eml_to_html/issues avec :
1. La commande exacte utilisée
2. Le HTML de sortie (ou un extrait)
3. Si possible, un `.eml` minimal reproduisant le problème (**sans données sensibles**)
