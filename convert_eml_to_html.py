import email
from email.policy import default
import os
import base64

def eml_to_html(eml_file, html_file):
    with open(eml_file, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=default)

    html_content = msg.get_body(preferencelist=('html')).get_content()

    # Extraire les images et les encoder en base64
    for part in msg.iter_attachments():
        if part.get_content_type() in ['image/jpeg', 'image/png', 'image/gif']:
            image_data = part.get_payload(decode=True)
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_name = part.get_filename()
            html_content = html_content.replace(image_name, f'data:{part.get_content_type()};base64,{image_base64}')

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    # Demander à l'utilisateur de spécifier le chemin du fichier EML
    eml_file = input("Veuillez entrer le chemin du fichier EML : ")

    # Vérifier si le fichier EML existe
    if not os.path.isfile(eml_file):
        print("Le fichier EML spécifié n'existe pas.")
        return

    # Obtenir le répertoire du fichier EML
    directory = os.path.dirname(eml_file)

    # Définir le chemin du fichier HTML
    html_file = os.path.join(directory, os.path.splitext(os.path.basename(eml_file))[0] + '.html')

    # Convertir le fichier EML en HTML
    eml_to_html(eml_file, html_file)

    # Informer l'utilisateur de la conversion réussie
    print(f"Le fichier HTML a été enregistré sous : {html_file}")

# Exemple d'utilisation
if __name__ == "__main__":
    main()