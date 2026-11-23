"""Exercise real parsers with disposable PDF bytes, never stored as report artifacts."""
import unittest
from unittest.mock import patch

import pymupdf
from backend.extraction import PDFError, extract_pdf, read_pdf


def pdf_bytes(text=None, pages=1, encrypted=False):
    with pymupdf.open() as doc:
        for _ in range(pages):
            page = doc.new_page()
            if text:
                page.insert_text((72, 72), text, fontsize=12)
        if encrypted:
            return doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256,
                               owner_pw="owner-test", user_pw="reader-test")
        return doc.tobytes()


REPORT = ("Consolidated Financial Results\nRs crore\nQ1 FY25 Q1 FY26\n"
          "Revenue 100000 120000\nEBITDA 36000 41000\nPAT 6800 13560")


class PDFReaderTests(unittest.TestCase):
    def test_actual_pdf_parsing(self):
        result = extract_pdf(pdf_bytes(REPORT))
        self.assertEqual(result["page_count"], 1)
        self.assertEqual(result["metrics"]["revenue"]["current"], 120000)
        self.assertEqual(result["metrics"]["pat"]["previous"], 6800)

    def test_pymupdf_fallback_when_pdfplumber_fails(self):
        with patch("pdfplumber.open", side_effect=ValueError("Synthetic primary-parser failure")):
            result = extract_pdf(pdf_bytes(REPORT))
        self.assertEqual(result["metrics"]["ebitda"]["current"], 41000)
        self.assertTrue(any("PyMuPDF" in message for message in result["warnings"]))

    def test_corrupt_pdf(self):
        with self.assertRaisesRegex(PDFError, "corrupt"):
            read_pdf(b"%PDF-1.7 invalid contents")

    def test_pdf_without_text_requires_ocr(self):
        with self.assertRaisesRegex(PDFError, "No selectable text"):
            read_pdf(pdf_bytes())

    def test_encrypted_pdf(self):
        with self.assertRaisesRegex(PDFError, "Password-protected"):
            read_pdf(pdf_bytes("Private test", encrypted=True))

    def test_page_limit(self):
        with self.assertRaisesRegex(PDFError, "200 pages"):
            read_pdf(pdf_bytes(pages=201))
