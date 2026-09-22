import base64
import subprocess
import sys
from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from eml_to_html import EmlToHtmlConverter, batch_convert
from eml_to_html import main as eml_to_html_main

PNG_1PX = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


def make_html_eml(html_body, charset='utf-8', subject='Test'):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = 'expediteur@example.com'
    msg['To'] = 'destinataire@example.com'
    msg.set_content('Fallback texte', subtype='plain', charset=charset)
    msg.add_alternative(html_body, subtype='html', charset=charset)
    return msg


def write_eml(tmp_path, msg, name='test.eml'):
    eml_path = tmp_path / name
    eml_path.write_bytes(msg.as_bytes())
    return eml_path


class TestHtmlBody:
    def test_meta_http_equiv_replaced(self, tmp_path):
        msg = make_html_eml(
            '<html><head><meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">'
            '</head><body><p>Bonjour</p></body></html>'
        )
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'charset=UTF-8' in result
        assert 'charset=iso-8859-1' not in result

    def test_meta_html5_replaced(self, tmp_path):
        msg = make_html_eml(
            '<html><head><meta charset="ISO-8859-1"></head><body><p>Bonjour</p></body></html>'
        )
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'charset=UTF-8' in result
        assert '<meta charset="ISO-8859-1"' not in result

    def test_meta_inserted_when_missing_head(self, tmp_path):
        msg = make_html_eml('<html><head></head><body><p>Sans meta</p></body></html>')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'charset=UTF-8' in result


class TestPlainBody:
    def test_plain_wrapped_in_html(self, tmp_path):
        msg = EmailMessage()
        msg['Subject'] = 'Texte seul'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.set_content('Première ligne\n<script>alert(1)</script>')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert '<!DOCTYPE html>' in result
        assert 'charset=UTF-8' in result
        assert '&lt;script&gt;' in result
        assert '<script>' not in result
        assert 'Première ligne<br>' in result

    def test_plain_images_not_processed(self, tmp_path):
        msg = EmailMessage()
        msg['Subject'] = 'Texte'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.set_content('Bonjour')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'data:image' not in result


class TestCharsetDecoding:
    def test_declared_iso8859_charset(self, tmp_path):
        msg = make_html_eml(
            '<html><head><meta charset="utf-8"></head><body><p>Éàü çàé</p></body></html>',
            charset='iso-8859-1',
        )
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'Éàü çàé' in result

    def test_invalid_declared_charset_falls_back(self, tmp_path):
        raw = (
            b'Subject: Test\n'
            b'MIME-Version: 1.0\n'
            b'Content-Type: text/html; charset="bogus-charset"\n'
            b'Content-Transfer-Encoding: 8bit\n'
            b'\n'
            + b'Texte correct <b>HTML</b>'
        )
        eml_path = tmp_path / 'broken.eml'
        eml_path.write_bytes(raw)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'Texte correct <b>HTML</b>' in result


class TestImageEmbedding:
    def make_image_eml(self, html_body, cid='<logo@example.com>', filename='logo.png'):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Avec image'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.attach(MIMEText('Fallback texte', 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        image = MIMEImage(PNG_1PX, _subtype='png')
        image.add_header('Content-Disposition', 'inline', filename=filename)
        if cid:
            image.add_header('Content-ID', cid)
        msg.attach(image)
        return msg

    def test_cid_replaced(self, tmp_path):
        msg = self.make_image_eml(
            '<html><head></head><body><img src="cid:logo@example.com"></body></html>'
        )
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'src="data:image/png;base64,' in result
        assert 'cid:logo@example.com' not in result
        assert base64.b64encode(PNG_1PX).decode('ascii') in result

    def test_filename_replaced_only_in_src(self, tmp_path):
        msg = self.make_image_eml(
            '<html><head></head><body>'
            '<p>Le fichier logo.png est joint.</p>'
            '<img src="logo.png">'
            '</body></html>'
        )
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'src="data:image/png;base64,' in result
        assert 'Le fichier logo.png est joint.' in result

    def test_webp_supported(self, tmp_path):
        msg = self.make_image_eml(
            '<html><head></head><body><img src="logo.png"></body></html>',
            cid=None,
        )
        image = msg.get_payload()[-1]
        image.replace_header('Content-Type', 'image/webp')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'src="data:image/webp;base64,' in result


class TestSave:
    def test_save_default_name(self, tmp_path):
        msg = make_html_eml('<html><head></head><body><p>Salut</p></body></html>')
        eml_path = write_eml(tmp_path, msg)
        out = EmlToHtmlConverter(eml_path).save()
        assert Path(out) == tmp_path / 'test.html'
        assert (tmp_path / 'test.html').read_text(encoding='utf-8').startswith('<html>')


class TestBatchConvert:
    def test_counts_success_and_failure(self, tmp_path):
        (tmp_path / 'bon.eml').write_bytes(
            make_html_eml('<html><head></head><body><p>OK</p></body></html>').as_bytes()
        )
        (tmp_path / 'mauvais.eml').write_bytes(
            b'Content-Type: multipart/mixed; boundary="B"\n'
            b'MIME-Version: 1.0\n'
            b'Subject: Casse\n'
            b'\n'
            b'--B\n'
            b'Content-Type: image/png\n'
            b'Content-Transfer-Encoding: base64\n'
            b'\n'
            b'!!!pas-base64!!!\n'
            b'--B--\n'
        )
        succeeded, failed = batch_convert(tmp_path)
        assert succeeded == 1
        assert failed == 1
        assert (tmp_path / 'bon.html').exists()

    def test_uppercase_extension_detected(self, tmp_path):
        (tmp_path / 'MAJ.EML').write_bytes(
            make_html_eml('<html><head></head><body><p>OK</p></body></html>').as_bytes()
        )
        succeeded, failed = batch_convert(tmp_path)
        assert succeeded == 1
        assert failed == 0

    def test_output_dir(self, tmp_path):
        out_dir = tmp_path / 'sortie'
        out_dir.mkdir()
        (tmp_path / 'a.eml').write_bytes(
            make_html_eml('<html><head></head><body><p>OK</p></body></html>').as_bytes()
        )
        batch_convert(tmp_path, out_dir)
        assert (out_dir / 'a.html').exists()

    def test_empty_dir(self, tmp_path):
        assert batch_convert(tmp_path) == (0, 0)


class TestLibraryUsage:
    def test_import_does_not_configure_logging(self):
        code = (
            "import eml_to_html, logging, sys; "
            "sys.exit(0 if not logging.root.handlers else 1)"
        )
        proc = subprocess.run(
            [sys.executable, '-c', code],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr.decode()

    def test_no_unused_os_import(self):
        source = Path(__file__).parent.parent.joinpath('eml_to_html.py').read_text()
        assert '\nimport os' not in source


class TestMainExitCodes:
    def test_missing_path_returns_error(self, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['eml_to_html.py', '/chemin/inexistant/eml'])
        assert eml_to_html_main() == 1

    def test_valid_single_file_returns_zero(self, tmp_path, monkeypatch):
        msg = make_html_eml('<html><head></head><body><p>OK</p></body></html>')
        eml_path = write_eml(tmp_path, msg)
        monkeypatch.setattr(sys, 'argv', ['eml_to_html.py', str(eml_path)])
        assert eml_to_html_main() == 0
        assert (tmp_path / 'test.html').exists()

    def test_batch_failure_returns_error(self, tmp_path, monkeypatch):
        (tmp_path / 'bon.eml').write_bytes(
            make_html_eml('<html><head></head><body><p>OK</p></body></html>').as_bytes()
        )
        (tmp_path / 'mauvais.eml').write_bytes(
            b'Content-Type: multipart/mixed; boundary="B"\n'
            b'MIME-Version: 1.0\n'
            b'Subject: Casse\n'
            b'\n'
            b'--B\n'
            b'Content-Type: image/png\n'
            b'Content-Transfer-Encoding: base64\n'
            b'\n'
            b'!!!pas-base64!!!\n'
            b'--B--\n'
        )
        monkeypatch.setattr(sys, 'argv', ['eml_to_html.py', str(tmp_path)])
        assert eml_to_html_main() == 1
