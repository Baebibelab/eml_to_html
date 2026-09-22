import email
from email.policy import default
import os
import base64
import re
import argparse
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class EmlToHtmlConverter:
    """Convertit un fichier EML en fichier HTML autonome (images en base64)."""

    IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'}
    META_PATTERN = re.compile(
        r'<meta\s+http-equiv=["\']Content-Type["\']\s+content=["\']text/html;\s*charset=[^"\']+["\']\s*/?>',
        re.IGNORECASE
    )

    def __init__(self, eml_path: str):
        self.eml_path = Path(eml_path)
        self.msg = None

    def load(self):
        with open(self.eml_path, 'rb') as f:
            self.msg = email.message_from_binary_file(f, policy=default)
        return self

    def _decode_body(self, body_part) -> str:
        raw_bytes = body_part.get_payload(decode=True)
        if raw_bytes is None:
            raise ValueError("Corps du message vide ou illisible.")

        declared_charset = body_part.get_content_charset()
        candidates = [declared_charset, 'utf-8', 'iso-8859-1']
        candidates = [c for c in candidates if c]  # retire les None

        for charset in candidates:
            try:
                return raw_bytes.decode(charset)
            except (UnicodeDecodeError, LookupError):
                continue

        logger.warning("Impossible de décoder proprement, fallback avec 'replace'.")
        return raw_bytes.decode('iso-8859-1', errors='replace')

    def _fix_meta_charset(self, html_content: str) -> str:
        new_meta = '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
        if self.META_PATTERN.search(html_content):
            return self.META_PATTERN.sub(new_meta, html_content)
        return re.sub(
            r'(<head[^>]*>)',
            r'\1\n' + new_meta,
            html_content,
            count=1,
            flags=re.IGNORECASE
        )

    def _embed_images(self, html_content: str) -> str:
        for part in self.msg.walk():
            content_type = part.get_content_type()
            if content_type not in self.IMAGE_TYPES:
                continue

            image_data = part.get_payload(decode=True)
            if not image_data:
                continue

            data_uri = f'data:{content_type};base64,{base64.b64encode(image_data).decode("ascii")}'
            content_id = part.get('Content-ID')

            if content_id:
                cid = content_id.strip('<>')
                if f'cid:{cid}' in html_content:
                    html_content = html_content.replace(f'cid:{cid}', data_uri)
                    continue

            image_name = part.get_filename()
            if image_name and image_name in html_content:
                html_content = html_content.replace(image_name, data_uri)

        return html_content

    def convert(self) -> str:
        if self.msg is None:
            self.load()

        body_part = self.msg.get_body(preferencelist=('html', 'plain'))
        if body_part is None:
            raise ValueError("Impossible de trouver un corps HTML ou texte dans cet email.")

        html_content = self._decode_body(body_part)
        html_content = self._fix_meta_charset(html_content)
        html_content = self._embed_images(html_content)
        return html_content

    def save(self, html_file: str = None) -> str:
        html_content = self.convert()
        if html_file is None:
            html_file = self.eml_path.with_suffix('.html')

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(html_file)


def batch_convert(input_dir: str, output_dir: str = None):
    """Convertit tous les fichiers .eml d'un dossier."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir

    eml_files = list(input_dir.glob('*.eml'))
    if not eml_files:
        logger.warning("Aucun fichier .eml trouvé dans %s", input_dir)
        return

    for eml_file in eml_files:
        try:
            html_file = output_dir / (eml_file.stem + '.html')
            converter = EmlToHtmlConverter(eml_file)
            converter.save(html_file)
            logger.info("✓ %s → %s", eml_file.name, html_file.name)
        except Exception as e:
            logger.error("✗ Échec pour %s : %s", eml_file.name, e)


def main():
    parser = argparse.ArgumentParser(description="Convertit des fichiers EML en HTML.")
    parser.add_argument('path', help="Chemin d'un fichier .eml ou d'un dossier")
    parser.add_argument('-o', '--output', help="Fichier ou dossier de sortie", default=None)
    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        logger.error("Le chemin spécifié n'existe pas : %s", path)
        return

    if path.is_dir():
        batch_convert(path, args.output)
    else:
        try:
            converter = EmlToHtmlConverter(path)
            html_file = converter.save(args.output)
            logger.info("Fichier HTML enregistré : %s", html_file)
        except Exception as e:
            logger.error("Erreur lors de la conversion : %s", e)


if __name__ == "__main__":
    main()