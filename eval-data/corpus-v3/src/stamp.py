"""Chèn header/footer cho PDF corpus v3 (pypdf + reportlab, font DejaVuSans)."""
import io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
CLS_COLOR = {"PUBLIC": "#2e7d32", "INTERNAL": "#1565c0", "CONFIDENTIAL": "#e65100", "RESTRICTED": "#c62828"}

def stamp(src, dst, code, version, cls):
    reader = PdfReader(src)
    writer = PdfWriter()
    n = len(reader.pages)
    for i, page in enumerate(reader.pages, 1):
        w = float(page.mediabox.width); h = float(page.mediabox.height)
        buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(w, h))
        c.setFont("DVB", 8); c.setFillColor(HexColor("#37474f"))
        c.drawString(42, h - 30, "NOVA DIGITAL TECHNOLOGY JSC")
        c.setFillColor(HexColor(CLS_COLOR[cls])); c.drawRightString(w - 42, h - 30, cls)
        c.setStrokeColor(HexColor("#cfd8dc")); c.setLineWidth(0.5)
        c.line(42, h - 36, w - 42, h - 36); c.line(42, 38, w - 42, 38)
        c.setFont("DV", 7.5); c.setFillColor(HexColor("#546e7a"))
        c.drawString(42, 26, f"{code} | Phiên bản {version} | {cls}")
        c.drawRightString(w - 42, 26, f"Trang {i}/{n}")
        c.save(); buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0]); writer.add_page(page)
    with open(dst, "wb") as f: writer.write(f)
