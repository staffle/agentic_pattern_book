#!/usr/bin/env python3
"""Compute and stamp visible PDF-wise page numbers onto a PDF.

Usage: stamp_page_numbers.py input.pdf [--out out.pdf]

This script computes visible page numbers (skipping blank pages) and stamps
numeric page labels at bottom-right for pages that are considered "visible".

Dependencies: pypdf, reportlab
Optional: PyMuPDF for more advanced text detection (not required here).
"""
import argparse
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
import io
import logging
import textwrap as tw

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def compute_visible_page_numbers(pdf_path:Path) -> list:
    reader = PdfReader(str(pdf_path))
    visible = []
    counter = 0
    for p in reader.pages:
        try:
            txt = p.extract_text() or ''
        except Exception:
            txt = ''
        if txt.strip():
            counter += 1
            visible.append(counter)
        else:
            visible.append(None)
    return visible


def stamp_page_numbers(pdf_path:Path, visible_numbers:list, out_path:Path|None=None, font_size:int=10, margin:float=36):
    if out_path is None:
        out_path = pdf_path.with_suffix('.paged.pdf')

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    for idx, page in enumerate(reader.pages):
        vis = None
        if idx < len(visible_numbers):
            vis = visible_numbers[idx]

        if vis is None:
            writer.add_page(page)
            continue

        mediabox = page.mediabox
        width = float(mediabox.right) - float(mediabox.left)
        height = float(mediabox.top) - float(mediabox.bottom)

        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(width, height))
        c.setFont('Helvetica', font_size)
        text = str(vis)
        text_width = c.stringWidth(text, 'Helvetica', font_size)
        x = width - margin - text_width
        y = margin / 2
        c.drawString(x, y, text)
        c.save()
        packet.seek(0)

        overlay = PdfReader(packet)
        try:
            page.merge_page(overlay.pages[0])
        except Exception:
            writer.add_page(page)
            continue

        writer.add_page(page)

    writer.write(str(out_path))
    writer.close()
    if out_path == pdf_path.with_suffix('.paged.pdf'):
        try:
            pdf_path.unlink()
        except Exception:
            pass
        out_path.rename(pdf_path)


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('input', help='Input PDF')
    ap.add_argument('--out', help='Output PDF (optional)')
    ap.add_argument('--dump-json', help='Dump computed visible numbers to JSON file and exit')
    args=ap.parse_args()
    input_pdf=Path(args.input)
    out_pdf = Path(args.out) if args.out else None

    vis = compute_visible_page_numbers(input_pdf)
    logging.info(f"Computed visible numbers: {sum(1 for v in vis if v is not None)} pages to stamp")
    if args.dump_json:
        import json
        with open(args.dump_json, 'w', encoding='utf-8') as f:
            json.dump(vis, f)
        logging.info(f"Dumped visible numbers to {args.dump_json}")
    else:
        stamp_page_numbers(input_pdf, vis, out_pdf)
        logging.info(f"Stamped page numbers into: {args.out or args.input}")
