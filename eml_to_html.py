import argparse
import base64
import email
import email.header
import html as html_module
import logging
import re
import sys
from email.policy import default
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar, Optional

logger = logging.getLogger(__name__)


class HtmlSanitizer(HTMLParser):
    """Filtre les éléments actifs d'un HTML d'email : scripts, handlers d'événements,
    iframes, formulaires, meta refresh et URI javascript:.

    Approche liste blanche : seules les balises et attributs explicitement autorisés
    sont conservés, tout le reste est retiré. Le contenu textuel est préservé."""

    ALLOWED_TAGS: ClassVar[frozenset] = frozenset({
        'a', 'abbr', 'acronym', 'address', 'area', 'article', 'aside', 'b', 'bdi', 'bdo',
        'blockquote', 'body', 'br', 'caption', 'center', 'cite', 'code', 'col', 'colgroup', 'dd',
        'del', 'details', 'dfn', 'div', 'dl', 'dt', 'em', 'figcaption', 'figure', 'footer',
        'font', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'header', 'hr', 'html', 'i',
        'img', 'ins', 'kbd', 'li', 'main', 'map', 'mark', 'meta', 'nav', 'noscript', 'ol',
        'p', 'pre', 'q', 'rp', 'rt', 'ruby', 's', 'samp', 'section', 'small', 'span',
        'strike', 'strong', 'style', 'sub', 'summary', 'sup', 'table', 'tbody', 'td',
        'tfoot', 'th', 'thead', 'time', 'title', 'tr', 'tt', 'u', 'ul', 'var', 'wbr',
    })
    DROP_WITH_CONTENT: ClassVar[frozenset] = frozenset({
        'script', 'noscript', 'iframe', 'frame', 'frameset', 'object', 'embed', 'applet',
        'template', 'form', 'input', 'button', 'select', 'textarea', 'option', 'link',
        'base', 'title',
    })
    URL_ATTRIBUTES: ClassVar[frozenset] = frozenset({
        'href', 'src', 'background', 'data-src', 'poster', 'action', 'formaction', 'cite',
        'longdesc', 'srcset', 'dynsrc', 'lowsrc', 'xlink:href',
    })
    ALLOWED_ATTRIBUTES: ClassVar[frozenset] = frozenset({
        'abbr', 'accept', 'align', 'alt', 'axis', 'border', 'cellpadding', 'cellspacing',
        'char', 'charoff', 'charset', 'checked', 'clear', 'color', 'cols', 'colspan',
        'compact', 'coords', 'datetime', 'dir', 'disabled', 'enctype', 'face', 'frame',
        'headers', 'height', 'hreflang', 'hspace', 'id', 'ismap', 'label', 'lang',
        'language', 'maxlength', 'media', 'multiple', 'name', 'noshade', 'nowrap',
        'open', 'readonly', 'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'shape',
        'size', 'sizes', 'span', 'start', 'summary', 'tabindex', 'target', 'type',
        'valign', 'value', 'vspace', 'width', 'class', 'style', 'title', 'role',
    })
    DANGEROUS_STYLE: ClassVar = re.compile(
        r'expression\s*\(|javascript\s*:|vbscript\s*:|-moz-binding|behavior\s*:',
        re.IGNORECASE
    )

    _VOID_TAGS: ClassVar[frozenset] = frozenset({
        'area', 'br', 'col', 'hr', 'img', 'meta', 'source', 'track', 'wbr',
    })

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self._skip_depth = 0

    @staticmethod
    def _is_dangerous_url(value: str) -> bool:
        value = html_module.unescape(value).strip().lower()
        value = re.sub(r'[\s\x00-\x1f]+', '', value)
        dangerous = ('javascript:', 'vbscript:', 'livescript:', 'mocha:')
        return value.startswith(dangerous) or 'data:text/html' in value

    def _is_allowed_attribute(self, name: str, value: str) -> bool:
        if name.startswith('on'):
            return False
        if name in self.URL_ATTRIBUTES:
            return not self._is_dangerous_url(value)
        if name == 'style':
            return not self.DANGEROUS_STYLE.search(html_module.unescape(value))
        return name in self.ALLOWED_ATTRIBUTES

    def _clean_attributes(self, tag, attrs):
        clean_attrs = []
        for name, value in attrs:
            if not name:
                continue
            lname = name.lower()
            if value is None:
                continue
            if tag == 'meta':
                if lname == 'charset':
                    clean_attrs.append((name, value))
                    continue
                if lname == 'http-equiv' and value.strip().lower() == 'content-type':
                    clean_attrs.append((name, value))
                    continue
                if lname == 'content' and value.lower().startswith('text/html'):
                    clean_attrs.append((name, value))
                    continue
                continue
            if self._is_allowed_attribute(lname, value):
                clean_attrs.append((name, value))
        return clean_attrs

    def handle_starttag(self, tag, attrs):
        if self._skip_depth:
            if tag in self.DROP_WITH_CONTENT and tag not in self.ALLOWED_TAGS:
                self._skip_depth += 1
            return
        if tag in self.DROP_WITH_CONTENT and tag not in self.ALLOWED_TAGS:
            self._skip_depth = 1
            return
        if tag not in self.ALLOWED_TAGS:
            return
        clean = self._clean_attributes(tag, attrs)
        self.out.append(self._build_tag(tag, clean, self_closing=False))

    def _build_tag(self, tag, attrs, self_closing):
        parts = ['<', tag]
        for name, value in attrs:
            if value is None:
                parts.append(f' {name}')
            else:
                escaped = value.replace('"', '&quot;')
                parts.append(f' {name}="{escaped}"')
        if self_closing or tag in self._VOID_TAGS:
            parts.append(' />')
        else:
            parts.append('>')
        return ''.join(parts)

    def handle_startendtag(self, tag, attrs):
        if self._skip_depth or tag in self.DROP_WITH_CONTENT or tag not in self.ALLOWED_TAGS:
            return
        self.out.append(self._build_tag(tag, self._clean_attributes(tag, attrs), self_closing=True))

    def handle_endtag(self, tag):
        if self._skip_depth:
            if tag in self.DROP_WITH_CONTENT and tag not in self.ALLOWED_TAGS:
                self._skip_depth -= 1
            return
        if tag in self.ALLOWED_TAGS and tag not in self._VOID_TAGS:
            self.out.append(f'</{tag}>')

    def handle_data(self, data):
        if not self._skip_depth:
            self.out.append(html_module.escape(data, quote=False))

    def handle_entityref(self, name):
        if not self._skip_depth:
            self.out.append(f'&{name};')

    def handle_comment(self, data):
        pass

    def handle_decl(self, decl):
        if not self._skip_depth and decl and decl.upper().startswith('DOCTYPE'):
            self.out.append(f'<!{decl}>')

    def result(self) -> str:
        return ''.join(self.out)


def sanitize_html(html_content: str) -> str:
    """Retire les éléments actifs d'un HTML d'email (scripts, handlers, iframes...)."""
    sanitizer = HtmlSanitizer()
    sanitizer.feed(html_content)
    sanitizer.close()
    cleaned = sanitizer.result()
    if HtmlSanitizer.DANGEROUS_STYLE.search(cleaned):
        cleaned = HtmlSanitizer.DANGEROUS_STYLE.sub('', cleaned)
    return cleaned


class EmlToHtmlConverter:
    """Convertit un fichier EML en fichier HTML autonome (images en base64)."""

    IMAGE_TYPES: ClassVar[frozenset] = frozenset(
        {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'}
    )
    META_PATTERN: ClassVar = re.compile(
        r'<meta\s+(?:http-equiv=["\']Content-Type["\']\s+)?'
        r'content=["\']text/html;\s*charset=[^"\']+["\']\s*/?>',
        re.IGNORECASE
    )
    CHARSET_PATTERN: ClassVar = re.compile(
        r'<meta\s+charset=["\'][^"\']+["\']\s*/?>',
        re.IGNORECASE
    )
    SRC_PATTERN: ClassVar = re.compile(
        r'(?P<prefix>(?:src|background|data-src)\s*=\s*)(?P<quote>["\'])(?P<url>.*?)(?P=quote)',
        re.IGNORECASE
    )

    def __init__(self, eml_path: str, sanitize: bool = True, extract_attachments: bool = False):
        self.eml_path = Path(eml_path)
        self.msg = None
        self.sanitize = sanitize
        self.extract_attachments = extract_attachments
        self.attachment_dir = None

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
        candidates = [c for c in candidates if c]

        for charset in candidates:
            try:
                return raw_bytes.decode(charset)
            except (UnicodeDecodeError, LookupError):
                continue

        logger.warning(
            "Impossible de décoder avec les charsets %s, fallback 'iso-8859-1' avec 'replace'.",
            ", ".join(candidates) or "inconnus"
        )
        return raw_bytes.decode('iso-8859-1', errors='replace')

    @staticmethod
    def _wrap_plain_text(text_content: str) -> str:
        escaped = html_module.escape(text_content)
        body = escaped.replace('\n', '<br>\n')
        return (
            '<!DOCTYPE html>\n<html>\n<head>\n'
            '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n'
            '<title>Email</title>\n</head>\n<body>\n<p>\n' + body + '\n</p>\n</body>\n</html>\n'
        )

    def _fix_meta_charset(self, html_content: str) -> str:
        new_meta = '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
        html_content = self.META_PATTERN.sub(new_meta, html_content, count=1)
        html_content = self.CHARSET_PATTERN.sub(new_meta, html_content, count=1)
        if new_meta in html_content:
            return html_content
        if re.search(r'<head[^>]*>', html_content, re.IGNORECASE):
            return re.sub(
                r'(<head[^>]*>)',
                r'\1\n' + new_meta,
                html_content,
                count=1,
                flags=re.IGNORECASE
            )
        match = re.search(r'<html[^>]*>', html_content, re.IGNORECASE)
        if match:
            head = '\n<head>\n' + new_meta + '\n</head>'
            return html_content[:match.end()] + head + html_content[match.end():]
        return new_meta + '\n' + html_content

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
            if image_name:
                html_content = self.SRC_PATTERN.sub(
                    lambda m, uri=data_uri, name=image_name: (
                        m.group('prefix') + m.group('quote') + uri + m.group('quote')
                        if m.group('url') == name else m.group(0)
                    ),
                    html_content
                )

        return html_content

    HEADER_FIELDS = (
        ('From', 'De'),
        ('To', 'À'),
        ('Cc', 'Cc'),
        ('Bcc', 'Cci'),
        ('Date', 'Date'),
        ('Subject', 'Objet'),
    )

    @staticmethod
    def _decode_header(value: str) -> str:
        decoded = email.header.decode_header(value)
        parts = []
        for text, charset in decoded:
            if isinstance(text, bytes):
                for candidate in (charset, 'utf-8', 'iso-8859-1'):
                    if not candidate:
                        continue
                    try:
                        text = text.decode(candidate)
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                if isinstance(text, bytes):
                    text = text.decode('iso-8859-1', errors='replace')
            parts.append(text)
        return ''.join(parts).strip()

    def _headers_html(self) -> str:
        rows = []
        for field, label in self.HEADER_FIELDS:
            raw_value = self.msg.get(field)
            if not raw_value:
                continue
            value = self._decode_header(str(raw_value))
            if not value:
                continue
            rows.append(
                f'<tr><th>{label}</th><td>{html_module.escape(value)}</td></tr>'
            )
        if not rows:
            return ''
        return (
            '<table class="eml-headers" border="1" cellpadding="4" cellspacing="0">\n'
            f'{chr(10).join(rows)}\n'
            '</table>\n<hr>\n'
        )

    DANGEROUS_EXTENSIONS: ClassVar[frozenset] = frozenset(
        {'html', 'htm', 'xhtml', 'svg', 'xml', 'mht', 'mhtml'}
    )

    @classmethod
    def _safe_filename(cls, name: str, fallback: str = 'piece-jointe') -> str:
        name = html_module.unescape(name or '')
        name = name.replace('\\', '/')
        name = name.split('/')[-1].strip()
        name = re.sub(r'[\x00-\x1f\x7f"*/:<>?|]', '_', name)
        name = name.strip('. ')
        if not name:
            return fallback
        extension = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
        if extension in cls.DANGEROUS_EXTENSIONS:
            name += '.txt'
        return name

    @staticmethod
    def _human_size(size: int) -> str:
        if size < 1024:
            return f'{size} o'
        if size < 1024 * 1024:
            return f'{size / 1024:.1f} Ko'
        return f'{size / (1024 * 1024):.1f} Mo'

    def _collect_attachments(self):
        attachments = []
        seen_names = {}
        for part in self.msg.walk():
            if part.is_multipart() or part.get_content_maintype() == 'multipart':
                continue
            if part is self.msg.get_body(preferencelist=('html', 'plain')):
                continue
            content_type = part.get_content_type()
            if content_type in self.IMAGE_TYPES:
                continue
            filename = part.get_filename()
            if not filename:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            safe_name = self._safe_filename(filename)
            seen_names[safe_name] = seen_names.get(safe_name, 0) + 1
            if seen_names[safe_name] > 1:
                stem, dot, ext = safe_name.rpartition('.')
                if not stem:
                    stem, ext = safe_name, ''
                    dot = ''
                safe_name = f'{stem}-{seen_names[safe_name]}{dot}{ext}'
            attachments.append({
                'filename': safe_name,
                'original_name': filename,
                'content_type': content_type,
                'size': len(payload),
                'payload': payload,
            })
        return attachments

    def _attachments_html(self, attachments) -> str:
        if not attachments:
            return ''
        rows = []
        for att in attachments:
            name = html_module.escape(att['filename'])
            ctype = html_module.escape(att['content_type'])
            size = self._human_size(att['size'])
            link = ''
            if self.attachment_dir is not None:
                target = f"{self.attachment_dir.name}/{att['filename']}"
                target = target.replace('"', '%22')
                link = f' — <a href="{target}">télécharger</a>'
            rows.append(
                f'<li><strong>{name}</strong> ({ctype}, {size}){link}</li>'
            )
        section = (
            '<hr>\n'
            '<h2>Pièces jointes</h2>\n'
            f'<ul>\n{chr(10).join(rows)}\n</ul>\n'
        )
        return section

    def _write_attachments(self, attachments, html_file: Path):
        if not attachments:
            return
        attachment_dir = html_file.parent / (html_file.stem + '_pieces-jointes')
        attachment_dir.mkdir(parents=True, exist_ok=True)
        self.attachment_dir = attachment_dir
        for att in attachments:
            target = attachment_dir / att['filename']
            with open(target, 'wb') as f:
                f.write(att['payload'])
            logger.info("Pièce jointe extraite : %s", target)

    def convert(self) -> str:
        if self.msg is None:
            self.load()

        body_part = self.msg.get_body(preferencelist=('html', 'plain'))
        if body_part is None:
            raise ValueError("Impossible de trouver un corps HTML ou texte dans cet email.")

        html_content = self._decode_body(body_part)

        if body_part.get_content_type() == 'text/plain':
            html_content = self._wrap_plain_text(html_content)
        else:
            html_content = self._fix_meta_charset(html_content)
            html_content = self._embed_images(html_content)
            if self.sanitize:
                html_content = sanitize_html(html_content)

        headers_section = self._headers_html()
        if headers_section:
            if '<body' in html_content.lower():
                match = re.search(r'<body[^>]*>', html_content, re.IGNORECASE)
                idx = match.end()
                html_content = html_content[:idx] + '\n' + headers_section + html_content[idx:]
            else:
                html_content = headers_section + html_content

        attachments = self._collect_attachments()
        if attachments:
            section = self._attachments_html(attachments)
            if '</body>' in html_content.lower():
                idx = html_content.lower().rfind('</body>')
                html_content = html_content[:idx] + section + html_content[idx:]
            else:
                html_content += '\n' + section
        return html_content

    def save(self, html_file: Optional[str] = None) -> str:
        if self.msg is None:
            self.load()
        if html_file is None:
            html_file = self.eml_path.with_suffix('.html')
        html_file = Path(html_file)

        attachments = self._collect_attachments()
        if self.extract_attachments and attachments:
            self._write_attachments(attachments, html_file)

        html_content = self.convert()
        self.attachment_dir = None

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(html_file)


def batch_convert(input_dir: str, output_dir: Optional[str] = None, sanitize: bool = True,
                   extract_attachments: bool = False, recursive: bool = False):
    """Convertit tous les fichiers .eml d'un dossier. Retourne (réussis, échecs).

    En mode récursif, les sous-dossiers sont parcourus et la structure est
    recréée dans le dossier de sortie."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir

    if recursive:
        eml_files = sorted(p for p in input_dir.rglob('*.eml') if p.is_file())
    else:
        eml_files = sorted(
            p for p in input_dir.iterdir()
            if p.is_file() and p.suffix.lower() == '.eml'
        )
    if not eml_files:
        logger.warning("Aucun fichier .eml trouvé dans %s", input_dir)
        return 0, 0

    succeeded, failed = 0, 0
    for eml_file in eml_files:
        try:
            html_file = _output_path_for(eml_file, input_dir, output_dir)
            html_file.parent.mkdir(parents=True, exist_ok=True)
            converter = EmlToHtmlConverter(
                eml_file, sanitize=sanitize, extract_attachments=extract_attachments
            )
            converter.save(html_file)
            succeeded += 1
            logger.info("✓ %s → %s", eml_file, html_file)
        except (OSError, ValueError, UnicodeError) as e:
            failed += 1
            logger.error("✗ Échec pour %s : %s", eml_file.name, e)

    return succeeded, failed


def _output_path_for(eml_file: Path, input_dir: Path, output_dir: Path) -> Path:
    """Chemin du HTML de sortie : à plat hors récursif, miroir de l'arborescence en récursif."""
    if eml_file.parent == input_dir:
        return output_dir / (eml_file.stem + '.html')
    relative = eml_file.parent.relative_to(input_dir)
    return output_dir / relative / (eml_file.stem + '.html')


def main():
    parser = argparse.ArgumentParser(description="Convertit des fichiers EML en HTML.")
    parser.add_argument('path', help="Chemin d'un fichier .eml ou d'un dossier")
    parser.add_argument('-o', '--output', help="Fichier ou dossier de sortie", default=None)
    parser.add_argument(
        '--no-sanitize',
        dest='sanitize',
        action='store_false',
        help="Désactive la sanitization du HTML de sortie (déconseillé pour des emails "
             "de source non fiable)"
    )
    parser.add_argument(
        '--sanitize',
        dest='sanitize',
        action='store_true',
        help="Obsolète : la sanitization est désormais active par défaut"
    )
    parser.set_defaults(sanitize=True)
    parser.add_argument(
        '--extract-attachments',
        action='store_true',
        help="Sauvegarde les pièces jointes non-image dans un dossier à côté du HTML "
             "et les liste en pied de page avec un lien de téléchargement"
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help="Parcourt aussi les sous-dossiers (l'arborescence est recréée dans la sortie)"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    path = Path(args.path)

    if not path.exists():
        logger.error("Le chemin spécifié n'existe pas : %s", path)
        return 1

    if path.is_dir():
        succeeded, failed = batch_convert(
            path, args.output,
            sanitize=args.sanitize,
            extract_attachments=args.extract_attachments,
            recursive=args.recursive,
        )
        if failed:
            logger.error("%d fichier(s) en échec sur %d traité(s).", failed, succeeded + failed)
            return 1
        return 0

    try:
        converter = EmlToHtmlConverter(
            path, sanitize=args.sanitize, extract_attachments=args.extract_attachments
        )
        html_file = converter.save(args.output)
        logger.info("Fichier HTML enregistré : %s", html_file)
    except (OSError, ValueError, UnicodeError) as e:
        logger.error("Erreur lors de la conversion : %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
