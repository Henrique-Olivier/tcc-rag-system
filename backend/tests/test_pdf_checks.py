import pymupdf
import pytest

from app.ingestion.pdf_checks import MSG_CORRUPTED, MSG_NO_TEXT, MSG_PASSWORD, PdfRejected, open_checked_pdf

TEXT = "Estudo sobre analgesia em felinos submetidos a ovariohisterectomia. " * 5


def _pdf(path, pages_text: list[str], **save_kwargs):
    doc = pymupdf.open()
    for text in pages_text:
        doc.new_page().insert_textbox(pymupdf.Rect(40, 40, 560, 800), text)
    doc.save(path, **save_kwargs)
    return path


def _rejection(path) -> str:
    with pytest.raises(PdfRejected) as info:
        open_checked_pdf(path)
    return info.value.message


def test_valid_pdf_passes(tmp_path):
    doc = open_checked_pdf(_pdf(tmp_path / "ok.pdf", [TEXT, TEXT]))

    assert doc.page_count == 2
    doc.close()


def test_corrupted_file_is_rejected(tmp_path):
    path = tmp_path / "ruim.pdf"
    path.write_bytes(b"isto nao e um pdf")

    assert _rejection(path) == MSG_CORRUPTED


def test_password_protected_pdf_is_rejected(tmp_path):
    path = _pdf(tmp_path / "senha.pdf", [TEXT], encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="x", owner_pw="y")

    assert _rejection(path) == MSG_PASSWORD


def test_pdf_without_text_is_rejected_as_scanned(tmp_path):
    path = _pdf(tmp_path / "escaneado.pdf", ["", "p. 2"])

    assert _rejection(path) == MSG_NO_TEXT
