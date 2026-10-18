"""Tiny helper so tests work with both old (fitz) and new (pymupdf) PyMuPDF."""
try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz


def blank_pdf(path):
    doc = fitz.open()
    doc.new_page()          # a page with no text = what a scanned image looks like to text extraction
    doc.save(str(path))
    doc.close()
