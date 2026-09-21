import email
from email.policy import default
import os

def eml_to_html(eml_file, html_file):
    with open(eml_file, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=default)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(msg.get_body(preferencelist=('html')).get_content())

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