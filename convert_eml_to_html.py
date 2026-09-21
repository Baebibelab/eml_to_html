import email
from email.policy import default
import os
import base64
import re


def fix_meta_charset(html_content):
    """
    Le HTML source contient une balise <meta charset> héritée de l'email
    d'origine (souvent Windows-1252 côté Outlook), alors que le contenu
    est décodé et réécrit en UTF-8. Sans correction de cette balise,
    le navigateur se fie à l'information (fausse) du meta tag et
    mal-interprète tout le texte accentué.
    """
    pattern = re.compile(
        r'<meta\s+http-equiv=["\']Content-Type["\']\s+content=["\']text/html;\s*charset=[^"\']+["\']\s*/?>',
        re.IGNORECASE
    )
    new_meta = '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'

    if pattern.search(html_content):
        html_content = pattern.sub(new_meta, html_content)
    else:
        # Aucune balise trouvée : on l'insère juste après <head>
        html_content = re.sub(
            r'(<head[^>]*>)',
            r'\1\n' + new_meta,
            html_content,
            count=1,
            flags=re.IGNORECASE
        )
    return html_content


def eml_to_html(eml_file, html_file):
    with open(eml_file, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=default)

    body_part = msg.get_body(preferencelist=('html', 'plain'))
    if body_part is None:
        raise ValueError("Impossible de trouver un corps HTML ou texte dans cet email.")

    raw_bytes = body_part.get_payload(decode=True)
    declared_charset = body_part.get_content_charset()

    try:
        html_content = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        charset = declared_charset or 'iso-8859-1'
        try:
            html_content = raw_bytes.decode(charset)
        except (UnicodeDecodeError, LookupError):
            html_content = raw_bytes.decode('iso-8859-1', errors='replace')

    # >>> Correction cruciale : aligner la balise meta sur l'encodage réel <<<
    html_content = fix_meta_charset(html_content)

    # --- Extraction des images inline ---
    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type not in ('image/jpeg', 'image/png', 'image/gif'):
            continue

        content_id = part.get('Content-ID')
        image_data = part.get_payload(decode=True)
        if not image_data:
            continue

        image_base64 = base64.b64encode(image_data).decode('ascii')
        data_uri = f'data:{content_type};base64,{image_base64}'

        replaced = False
        if content_id:
            cid = content_id.strip('<>')
            new_content = html_content.replace(f'cid:{cid}', data_uri)
            if new_content != html_content:
                html_content = new_content
                replaced = True

        if not replaced:
            image_name = part.get_filename()
            if image_name and image_name in html_content:
                html_content = html_content.replace(image_name, data_uri)

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


def main():
    eml_file = input("Veuillez entrer le chemin du fichier EML : ")

    if not os.path.isfile(eml_file):
        print("Le fichier EML spécifié n'existe pas.")
        return

    directory = os.path.dirname(eml_file)
    html_file = os.path.join(directory, os.path.splitext(os.path.basename(eml_file))[0] + '.html')

    eml_to_html(eml_file, html_file)

    print(f"Le fichier HTML a été enregistré sous : {html_file}")


if __name__ == "__main__":
    main()