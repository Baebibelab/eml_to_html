import base64
import subprocess
import sys
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pytest

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


class TestSanitizer:
    PAYLOADS = [
        ('script block', '<p>Texte</p><script>alert(1)</script>', '<p>Texte</p>'),
        ('img onerror', '<img src="x" onerror="alert(1)">', '<img src="x" />'),
        ('javascript href', '<a href="javascript:alert(1)">clic</a>', '<a>clic</a>'),
        ('obfuscated href', '<a href="  jaVaScRiPt&#58;alert(1)">clic</a>', '<a>clic</a>'),
        ('iframe', '<iframe src="https://evil.com"></iframe>', ''),
        ('meta refresh',
         '<meta http-equiv="refresh" content="0;url=https://evil.com">',
         '<meta />'),
        ('form', '<form action="https://evil.com"><input type="password" name="pw"></form>', ''),
        ('onclick', '<div onclick="steal()">clic</div>', '<div>clic</div>'),
        ('comment', '<p>a</p><!-- <script>alert(1)</script> --><p>b</p>', '<p>a</p><p>b</p>'),
        ('nested skip', '<script>if (1 < 2) { alert("<b>") }</script><p>ok</p>', '<p>ok</p>'),
        ('unclosed script', '<script>alert(1)<p>suite</p>', ''),
        ('style expression', '<div style="color: expression(alert(1))">x</div>', '<div>x</div>'),
        ('style js url',
         '<div style="background: url(javascript:alert(1))">x</div>',
         '<div>x</div>'),
        ('data html', '<a href="data:text/html,<script>alert(1)</script>">x</a>', '<a>x</a>'),
    ]

    @staticmethod
    def _eml_with(html_body):
        msg = EmailMessage()
        msg['Subject'] = 'Test sanitize'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.set_content('fallback')
        msg.add_alternative(html_body, subtype='html')
        return msg

    def test_payloads_neutralized_via_convert(self, tmp_path):
        for name, payload, expected in self.PAYLOADS:
            html_body = f'<html><head></head><body>{payload}</body></html>'
            eml_path = write_eml(tmp_path, self._eml_with(html_body))
            result = EmlToHtmlConverter(eml_path, sanitize=True).convert()
            body = result.split('<body', 1)[1]
            body = body.split('>', 1)[1]
            body = body.rsplit('</body>', 1)[0]
            if '<hr>' in body:
                body = body.split('<hr>', 1)[1]
            assert body.strip() == expected.strip(), f'{name}: {body!r} != {expected!r}'

    def test_safe_content_preserved(self, tmp_path):
        html_body = (
            '<html><head><meta charset="utf-8"></head><body>'
            '<h1 class="t">Titre</h1>'
            '<table><tr><td align="center">cell</td></tr></table>'
            '<img src="cid:logo@example.com" alt="logo" width="10">'
            '<a href="https://example.com" target="_blank">site</a>'
            '<img src="data:image/png;base64,AAA">'
            '<div style="color: red">ok</div>'
            '</body></html>'
        )
        msg = self._eml_with(html_body)
        msg.get_payload()[1].add_attachment = None
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path, sanitize=True).convert()
        assert 'Titre' in result
        assert '<table><tr><td align="center">cell</td></tr></table>' in result
        assert 'src="cid:logo@example.com"' in result
        assert 'href="https://example.com"' in result
        assert 'src="data:image/png;base64,AAA"' in result
        assert 'style="color: red"' in result
        assert 'charset=UTF-8' in result

    def test_disabled_by_default(self, tmp_path):
        html_body = '<html><head></head><body><script>alert(1)</script></body></html>'
        eml_path = write_eml(tmp_path, self._eml_with(html_body))
        result = EmlToHtmlConverter(eml_path).convert()
        assert '<script>alert(1)</script>' in result

    def test_cid_images_embedded_then_sanitized(self, tmp_path):
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'img'
        msg.attach(MIMEText('fallback', 'plain', 'utf-8'))
        msg.attach(MIMEText(
            '<html><head></head><body>'
            '<img src="cid:logo@example.com" onerror="alert(1)"></body></html>',
            'html', 'utf-8'))
        image = MIMEImage(PNG_1PX, _subtype='png')
        image.add_header('Content-ID', '<logo@example.com>')
        msg.attach(image)
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path, sanitize=True).convert()
        assert 'src="data:image/png;base64,' in result
        assert 'onerror' not in result

    def test_cli_flag(self, tmp_path, monkeypatch):
        html_body = '<html><head></head><body><script>alert(1)</script></body></html>'
        eml_path = write_eml(tmp_path, self._eml_with(html_body))
        monkeypatch.setattr(sys, 'argv', ['eml_to_html.py', str(eml_path), '--sanitize'])
        assert eml_to_html_main() == 0
        out = (tmp_path / 'test.html').read_text(encoding='utf-8')
        assert '<script>' not in out


class TestAttachments:
    @staticmethod
    def _eml_with_attachment(html_body, filename, content=b'%PDF-fake', subtype='pdf'):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'avec PJ'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.attach(MIMEText('fallback', 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        att = MIMEApplication(content, _subtype=subtype)
        att.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(att)
        return msg

    def test_listed_in_html_by_default(self, tmp_path):
        msg = self._eml_with_attachment(
            '<html><head></head><body><p>Corps</p></body></html>', 'rapport.pdf'
        )
        eml_path = write_eml(tmp_path, msg)
        converter = EmlToHtmlConverter(eml_path)
        out = converter.save(tmp_path / 'out.html')
        html_out = Path(out).read_text(encoding='utf-8')
        assert 'Pièces jointes' in html_out
        assert 'rapport.pdf' in html_out
        assert 'application/pdf' in html_out
        assert 'Ko' in html_out or ' o' in html_out
        assert not (tmp_path / 'out_pieces-jointes').exists()

    def test_extract_flag_writes_files_and_links(self, tmp_path):
        msg = self._eml_with_attachment(
            '<html><head></head><body><p>Corps</p></body></html>', 'rapport.pdf'
        )
        eml_path = write_eml(tmp_path, msg)
        converter = EmlToHtmlConverter(eml_path, extract_attachments=True)
        out = converter.save(tmp_path / 'out.html')
        att_dir = tmp_path / 'out_pieces-jointes'
        extracted = list(att_dir.iterdir())
        assert len(extracted) == 1
        assert extracted[0].name == 'rapport.pdf'
        assert extracted[0].read_bytes() == b'%PDF-fake'
        html_out = Path(out).read_text(encoding='utf-8')
        assert 'télécharger' in html_out
        assert 'out_pieces-jointes/rapport.pdf' in html_out

    def test_path_traversal_neutralized(self, tmp_path):
        msg = self._eml_with_attachment(
            '<html><head></head><body><p>Corps</p></body></html>',
            '../../etc/passwd.docx', content=b'evil'
        )
        eml_path = write_eml(tmp_path, msg)
        converter = EmlToHtmlConverter(eml_path, extract_attachments=True)
        converter.save(tmp_path / 'out.html')
        att_dir = tmp_path / 'out_pieces-jointes'
        names = [p.name for p in att_dir.iterdir()]
        assert names == ['passwd.docx']
        assert (att_dir / 'passwd.docx').read_bytes() == b'evil'
        assert not (tmp_path / 'etc').exists()
        assert not Path('/workspace/etc/passwd.docx').exists()

    def test_duplicate_filenames_deduplicated(self, tmp_path):
        msg = MIMEMultipart()
        msg['Subject'] = 'doublons'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.attach(MIMEText('<html><head></head><body><p>x</p></body></html>', 'html', 'utf-8'))
        for content in (b'premier', b'second'):
            att = MIMEApplication(content, _subtype='pdf')
            att.add_header('Content-Disposition', 'attachment', filename='doc.pdf')
            msg.attach(att)
        eml_path = write_eml(tmp_path, msg)
        converter = EmlToHtmlConverter(eml_path, extract_attachments=True)
        converter.save(tmp_path / 'out.html')
        att_dir = tmp_path / 'out_pieces-jointes'
        names = sorted(p.name for p in att_dir.iterdir())
        assert names == ['doc-2.pdf', 'doc.pdf']
        assert (att_dir / 'doc.pdf').read_bytes() == b'premier'
        assert (att_dir / 'doc-2.pdf').read_bytes() == b'second'

    def test_inline_images_not_listed_as_attachments(self, tmp_path):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'inline'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.attach(MIMEText('fallback', 'plain', 'utf-8'))
        msg.attach(MIMEText(
            '<html><head></head><body>'
            '<img src="cid:logo@example.com"></body></html>', 'html', 'utf-8'
        ))
        image = MIMEImage(PNG_1PX, _subtype='png')
        image.add_header('Content-ID', '<logo@example.com>')
        msg.attach(image)
        eml_path = write_eml(tmp_path, msg)
        converter = EmlToHtmlConverter(eml_path)
        out = converter.save(tmp_path / 'out.html')
        html_out = Path(out).read_text(encoding='utf-8')
        assert 'Pièces jointes' not in html_out
        assert 'data:image/png;base64,' in html_out

    def test_plain_text_with_attachment(self, tmp_path):
        m = EmailMessage()
        m['Subject'] = 'plain'
        m['From'] = 'a@example.com'
        m['To'] = 'b@example.com'
        m.set_content('texte seul')
        m.add_attachment(b'%PDF-3', maintype='application', subtype='pdf', filename='doc.pdf')
        eml_path = write_eml(tmp_path, m)
        converter = EmlToHtmlConverter(eml_path)
        out = converter.save(tmp_path / 'out.html')
        html_out = Path(out).read_text(encoding='utf-8')
        assert 'Pièces jointes' in html_out
        assert 'doc.pdf' in html_out

    def test_batch_flag(self, tmp_path, monkeypatch):
        (tmp_path / 'a.eml').write_bytes(
            self._eml_with_attachment(
                '<html><head></head><body><p>x</p></body></html>', 'f.pdf', content=b'X'
            ).as_bytes()
        )
        monkeypatch.setattr(sys, 'argv',
                            ['eml_to_html.py', str(tmp_path), '--extract-attachments'])
        assert eml_to_html_main() == 0
        assert (tmp_path / 'a_pieces-jointes' / 'f.pdf').exists()
        html_out = (tmp_path / 'a.html').read_text(encoding='utf-8')
        assert 'télécharger' in html_out


class TestPackaging:
    def test_entry_point_registered_when_installed(self):
        pytest.importorskip('importlib.metadata')
        from importlib.metadata import distribution
        try:
            dist = distribution('eml-to-html')
        except Exception:
            pytest.skip('paquet non installé dans cet environnement')
        console = dist.entry_points
        assert 'eml-to-html' in [ep.name for ep in console if ep.group == 'console_scripts']

    def test_module_has_main_callable(self):
        import eml_to_html
        assert callable(eml_to_html.main)

    def test_pyproject_declares_no_dependencies(self):
        root = Path(__file__).parent.parent
        content = root.joinpath('pyproject.toml').read_text(encoding='utf-8')
        assert 'dependencies = []' in content
        assert '[project.scripts]' in content
        assert 'eml-to-html = "eml_to_html:main"' in content


class TestRecursiveBatch:
    @staticmethod
    def _make_tree(tmp_path):
        (tmp_path / 'a.eml').write_bytes(
            make_html_eml('<html><head></head><body><p>r a</p></body></html>').as_bytes()
        )
        sub = tmp_path / 'archives'
        sub.mkdir()
        (sub / 'b.eml').write_bytes(
            make_html_eml('<html><head></head><body><p>r b</p></body></html>').as_bytes()
        )
        deep = sub / '2023'
        deep.mkdir()
        (deep / 'c.eml').write_bytes(
            make_html_eml('<html><head></head><body><p>r c</p></body></html>').as_bytes()
        )

    def test_non_recursive_ignores_subdirs(self, tmp_path):
        self._make_tree(tmp_path)
        succeeded, failed = batch_convert(tmp_path)
        assert (succeeded, failed) == (1, 0)
        assert (tmp_path / 'a.html').exists()
        assert not (tmp_path / 'archives' / 'b.html').exists()

    def test_recursive_converts_all_and_mirrors_tree(self, tmp_path):
        self._make_tree(tmp_path)
        succeeded, failed = batch_convert(tmp_path, recursive=True)
        assert (succeeded, failed) == (3, 0)
        assert (tmp_path / 'a.html').exists()
        assert (tmp_path / 'archives' / 'b.html').exists()
        assert (tmp_path / 'archives' / '2023' / 'c.html').exists()

    def test_recursive_with_output_dir_mirrors_tree(self, tmp_path):
        self._make_tree(tmp_path)
        out = tmp_path / 'sortie'
        succeeded, failed = batch_convert(tmp_path, out, recursive=True)
        assert (succeeded, failed) == (3, 0)
        assert (out / 'a.html').exists()
        assert (out / 'archives' / 'b.html').exists()
        assert (out / 'archives' / '2023' / 'c.html').exists()
        assert not (tmp_path / 'a.html').exists()

    def test_recursive_with_extract_attachments(self, tmp_path):
        sub = tmp_path / 'doss'
        sub.mkdir()
        msg = TestAttachments._eml_with_attachment(
            '<html><head></head><body><p>x</p></body></html>', 'f.pdf', content=b'X'
        )
        (sub / 'a.eml').write_bytes(msg.as_bytes())
        succeeded, failed = batch_convert(
            tmp_path, extract_attachments=True, recursive=True
        )
        assert (succeeded, failed) == (1, 0)
        att_dir = sub / 'a_pieces-jointes'
        assert (att_dir / 'f.pdf').exists()

    def test_cli_recursive_flag(self, tmp_path, monkeypatch):
        self._make_tree(tmp_path)
        monkeypatch.setattr(sys, 'argv', ['eml_to_html.py', str(tmp_path), '--recursive'])
        assert eml_to_html_main() == 0
        assert (tmp_path / 'archives' / 'b.html').exists()
        assert (tmp_path / 'archives' / '2023' / 'c.html').exists()


class TestHeaders:
    @staticmethod
    def _eml_with_headers(from_=None, to=None, cc=None, bcc=None, subject='Objet test',
                          html_body='<html><head></head><body><p>Corps</p></body></html>',
                          plain=False):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        if from_:
            msg['From'] = from_
        if to:
            msg['To'] = to
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc
        if plain:
            msg.attach(MIMEText('texte brut', 'plain', 'utf-8'))
        else:
            msg.attach(MIMEText('fallback', 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        return msg

    def test_headers_shown_in_html(self, tmp_path):
        msg = self._eml_with_headers(
            from_='romain@example.com',
            to='client@example.com, direction@example.com',
            cc='compta@example.com',
        )
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert '<table class="eml-headers"' in result
        assert '<th>De</th>' in result and 'romain@example.com' in result
        assert '<th>À</th>' in result
        assert 'client@example.com, direction@example.com' in result
        assert '<th>Cc</th>' in result and 'compta@example.com' in result
        assert '<th>Objet</th>' in result and 'Objet test' in result
        assert '<th>Cci</th>' not in result
        assert result.index('<table') < result.index('<p>Corps</p>')

    def test_encoded_words_decoded(self, tmp_path):
        msg = self._eml_with_headers(
            from_='=?utf-8?Q?Romain_BEAL?= <romain@example.com>',
            subject='=?utf-8?Q?Rapport_trimestriel_=E2=82=AC?=',
        )
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert 'Romain BEAL &lt;romain@example.com&gt;' in result
        assert 'Rapport trimestriel €' in result
        assert '=?utf-8?' not in result

    def test_bcc_shown_when_present(self, tmp_path):
        msg = self._eml_with_headers(from_='a@example.com', to='b@example.com',
                                     bcc='secret@example.com')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert '<th>Cci</th>' in result
        assert 'secret@example.com' in result

    def test_headers_in_plain_text_fallback(self, tmp_path):
        msg = self._eml_with_headers(from_='a@example.com', to='b@example.com', plain=True)
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert '<th>De</th>' in result and 'a@example.com' in result
        assert '<th>Objet</th>' in result

    def test_headers_survive_sanitize(self, tmp_path):
        msg = self._eml_with_headers(
            from_='=?utf-8?Q?Romain?= <r@example.com>',
            to='c@example.com',
        )
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path, sanitize=True).convert()
        assert 'r@example.com' in result
        assert '<th>Objet</th>' in result

    def test_header_values_escaped(self, tmp_path):
        msg = self._eml_with_headers(from_='a@example.com', to='b@example.com',
                                     subject='<script>alert(1)</script>')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToHtmlConverter(eml_path).convert()
        assert '<script>' not in result
        assert '&lt;script&gt;' in result
