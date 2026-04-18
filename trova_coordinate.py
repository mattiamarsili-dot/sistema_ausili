"""
Strumento per trovare le coordinate esatte nei PDF statici.
Genera una versione del PDF con griglia e marcatori numerati.

Uso: python3 trova_coordinate.py
Output: data/output/GRIGLIA_<nome_file>.pdf  (aprilo e identifica le coordinate)
"""
import os, sys
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "data", "pdf_templates")
OUTPUT_DIR    = os.path.join(os.path.dirname(__file__), "data", "output")

def genera_griglia(pdf_path: str, passo: int = 50):
    """Sovrappone una griglia con coordinate ogni `passo` punti."""
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page_num, page in enumerate(reader.pages):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(w, h))

        # Griglia verticale (x)
        x = 0
        while x <= w:
            c.setStrokeColorRGB(0.7, 0.7, 1)
            c.setLineWidth(0.3)
            c.line(x, 0, x, h)
            if x % 100 == 0:
                c.setFillColorRGB(0, 0, 0.8)
                c.setFont("Helvetica-Bold", 7)
                c.drawString(x + 1, h - 12, str(int(x)))
            x += passo

        # Griglia orizzontale (y)
        y = 0
        while y <= h:
            c.setStrokeColorRGB(1, 0.7, 0.7)
            c.setLineWidth(0.3)
            c.line(0, y, w, y)
            if y % 100 == 0:
                c.setFillColorRGB(0.8, 0, 0)
                c.setFont("Helvetica-Bold", 7)
                c.drawString(3, y + 1, str(int(y)))
            y += passo

        # Intestazione pagina
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(10, h - 25, f"Pagina {page_num} — larghezza={w:.0f}pt, altezza={h:.0f}pt")

        c.save()
        packet.seek(0)

        from pypdf import PdfReader as PR
        ov = PR(packet)
        page.merge_page(ov.pages[0])
        writer.add_page(page)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    nome_base = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(OUTPUT_DIR, f"GRIGLIA_{nome_base}.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"✅ Griglia salvata in: {output_path}")
    return output_path


def test_overlay(pdf_path: str, punti: list):
    """
    Testa il posizionamento di testo su coordinate specifiche.
    punti: lista di (pagina, x, y, testo)
    """
    from pdf_compiler import compila_overlay_pdf
    overlay_config = [
        {"pagina": p, "x": x, "y": y, "chiave_dati": f"_test_{i}", "font_size": 10}
        for i, (p, x, y, _) in enumerate(punti)
    ]
    # Prepara dati test
    dati = {f"_test_{i}": testo for i, (_, _, _, testo) in enumerate(punti)}
    nome_base = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(OUTPUT_DIR, f"TEST_{nome_base}.pdf")
    compila_overlay_pdf(pdf_path, overlay_config, dati, output_path)
    print(f"✅ Test salvato in: {output_path}")


if __name__ == "__main__":
    # Elenca i template disponibili
    pdfs = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".pdf")]
    if not pdfs:
        print("Nessun PDF in data/pdf_templates/")
        sys.exit(1)

    print("Template disponibili:")
    for i, f in enumerate(pdfs):
        print(f"  {i}: {f}")

    scelta = input("Scegli numero (invio per 0): ").strip()
    idx = int(scelta) if scelta else 0
    pdf_path = os.path.join(TEMPLATES_DIR, pdfs[idx])

    print(f"\nGenerazione griglia su: {pdfs[idx]}")
    genera_griglia(pdf_path)
    print("\nApri il PDF con griglia, identifica le coordinate dei campi,")
    print("poi aggiorna il file config/Deleghe_Rm3_mapping.json")
