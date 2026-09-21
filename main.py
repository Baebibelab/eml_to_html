import email
from email.policy import default

def eml_to_html(eml_file, html_file):
    with open(eml_file, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=default)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(msg.get_body(preferencelist=('html')).get_content())

# Exemple d'utilisation
eml_to_html('votre_fichier.eml', 'votre_fichier.html')