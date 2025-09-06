#!/usr/bin/env python3
"""
Compile the Agentic Design Patterns book.

- Extract URLs from a preprint PDF (annotations and plain text),
- Normalize Google Docs/Sheets/Slides to direct PDF export links,
- Download or export linked docs to PDF, and scrape Drive folders (public).
- Merge all PDFs with a cover and optional table of contents.
- Append a references page listing any unresolved links.

Usage example:

python build_book.py \
  --index-pdf "Agentic Design Patterns.pdf.pdf" \
  --cover "cover.jpg" \
  --out "Agentic_Design_Patterns_compiled.pdf" \
  --workdir "_agentic_build" \
  --add-toc

"""
import argparse
import os
import re
import csv
from pathlib import Path
import shutil
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader, PdfWriter
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from tqdm import tqdm
import textwrap as tw
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    import fitz
    HAVE_FITZ = True
except Exception:
    fitz = None
    HAVE_FITZ = False

A4_PX_300DPI=(2480,3508)
A4_PX_72DPI=(595,842)  # Standard PDF size
URL_RE=re.compile(r'(https?://[^\s\]\)<>"]+)',re.IGNORECASE)

def safe_name(s,maxlen=120):
    import re
    s=re.sub(r'[\s/\\:*?"<>|]+','_',s.strip())
    s=re.sub(r'_+','_',s).strip('_')
    return s[:maxlen] if len(s)>maxlen else s

def ensure_dir(p:Path):
    p.mkdir(parents=True,exist_ok=True)


def extract_pdf_links(index_pdf:Path):
    logging.info(f"Extracting links from PDF: {index_pdf}")
    links=[]; seen=set()
    reader=PdfReader(str(index_pdf))
    for page in reader.pages:
        annots=page.get('/Annots')
        if annots:
            for a in annots:
                obj=a.get_object()
                if '/A' in obj and '/URI' in obj['/A']:
                    url=obj['/A']['/URI']
                    if isinstance(url,str) and url not in seen:
                        links.append(url); seen.add(url)
    for page in reader.pages:
        try:
            txt=page.extract_text() or ''
        except Exception:
            txt=''
        for m in URL_RE.finditer(txt):
            url=m.group(1).strip().rstrip(',.);]')
            if url not in seen:
                links.append(url); seen.add(url)
    logging.info(f"Extracted {len(links)} links from PDF.")
    return links


def extract_pdf_headings(index_pdf:Path):
    """Return the predefined list of TOC headings from the provided TOC content."""
    logging.info(f"Using predefined TOC headings from provided content.")
    headings = [
        "Dedication",
        "Acknowledgment",
        "Foreword",
        "A Thought Leader's Perspective: Power and Responsibility",
        "Introduction",
        "What makes an AI system an \"agent\"?",
        "Part One",
        "Chapter 1: Prompt Chaining ",
        "Chapter 2: Routing ",
        "Chapter 3: Parallelization ",
        "Chapter 4: Reflection ",
        "Chapter 5: Tool Use ",
        "Chapter 6: Planning ",
        "Chapter 7: Multi-Agent ",
        "Part Two",
        "Chapter 8: Memory Management ",
        "Chapter 9: Learning and Adaptation ",
        "Chapter 10: Model Context Protocol (MCP) ",
        "Chapter 11: Goal Setting and Monitoring ",
        "Part Three",
        "Chapter 12: Exception Handling and Recovery ",
        "Chapter 13: Human-in-the-Loop ",
        "Chapter 14: Knowledge Retrieval (RAG) ",
        "Part Four",
        "Chapter 15: Inter-Agent Communication (A2A) ",
        "Chapter 16: Resource-Aware Optimization ",
        "Chapter 17: Reasoning Techniques ",
        "Chapter 18: Guardrails/Safety Patterns ",
        "Chapter 19: Evaluation and Monitoring ",
        "Chapter 20: Prioritization ",
        "Chapter 21: Exploration and Discovery ",
        "Appendix",
        "Appendix A: Advanced Prompting Techniques",
        "Appendix B - AI Agentic ....: From GUI to Real world environment",
        "Appendix C - Quick overview of Agentic Frameworks",
        "Appendix D - Building an Agent with AgentSpace (on-line only)",
        "Appendix E - AI Agents on the CLI (online)",
        "Appendix F - Under the Hood: An Inside Look at the Agents’ Reasoning Engines",
        "Appendix G - Coding agents",
        "Conclusion",
        "Glossary",
        "Index of Terms"
    ]
    logging.info(f"Extracted {len(headings)} predefined headings.")
    return headings


def pil_cover_to_pdf(img_path:Path, out_pdf:Path):
    img=Image.open(img_path).convert('RGB')
    w,h=img.size
    target_w,target_h=A4_PX_72DPI  # Use smaller size for cover
    scale=min(target_w/w,target_h/h)
    new_w,new_h=int(w*scale),int(h*scale)
    canvas=Image.new('RGB',A4_PX_72DPI,'white')
    img_resized=img.resize((new_w,new_h),Image.LANCZOS)
    off_x=(target_w-new_w)//2
    off_y=(target_h-new_h)//2
    canvas.paste(img_resized,(off_x,off_y))
    canvas.save(out_pdf)

def normalize_gdoc(url):
    m=re.search(r'docs\.google\.com/document/d/([\w-]+)',url)
    return f'https://docs.google.com/document/d/{m.group(1)}/export?format=pdf' if m else None

def normalize_gsheet(url):
    m=re.search(r'docs\.google\.com/spreadsheets/d/([\w-]+)',url)
    return f'https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=pdf' if m else None

def normalize_gslides(url):
    m=re.search(r'docs\.google\.com/presentation/d/([\w-]+)',url)
    return f'https://docs.google.com/presentation/d/{m.group(1)}/export/pdf' if m else None

def drive_file_id_from_url(url):
    m=re.search(r'drive\.google\.com/file/d/([\w-]+)',url)
    if m: return m.group(1)
    u=urlparse(url)
    qs=parse_qs(u.query)
    if 'id' in qs: return qs['id'][0]
    return None

def is_drive_folder(url):
    m=re.search(r'drive\.google\.com/drive/(?:u/\d+/)?folders/([\w-]+)',url)
    return m.group(1) if m else None

def guess_title(url:str)->str:
    u=urlparse(url)
    host=u.netloc
    path=u.path.strip('/').replace('/',' / ')
    return f"{host} — {path or host}"

def fetch_url_to_pdf(url,out_dir:Path,session:requests.Session,timeout=60):
    logging.info(f"Fetching PDF from URL: {url}")
    ensure_dir(out_dir)
    export_url=(normalize_gdoc(url) or normalize_gsheet(url) or normalize_gslides(url))
    if export_url:
        url=export_url
    file_id=drive_file_id_from_url(url)
    if file_id and 'uc?export=download' not in url and 'document/d' not in url:
        url=f'https://drive.google.com/uc?export=download&id={file_id}'
    title=guess_title(url)
    fname=safe_name(title)+'.pdf'
    out_path=out_dir/fname
    # Check if already downloaded and valid
    if out_path.exists():
        try:
            PdfReader(str(out_path))
            logging.info(f"PDF already exists and is valid: {out_path}")
            return out_path
        except Exception:
            logging.warning(f"Existing file is invalid, re-downloading: {out_path}")
            out_path.unlink()
    headers={'User-Agent':'Mozilla/5.0'}
    try:
        with session.get(url,headers=headers,stream=True,timeout=timeout) as r:
            if 'confirm=' in r.url and 'uc?export=download' in r.url:
                with session.get(r.url,headers=headers,stream=True,timeout=timeout) as r2:
                    r=r2
            ctype=r.headers.get('Content-Type','').lower()
            if r.status_code!=200:
                logging.error(f"HTTP {r.status_code} for URL: {url}")
                return None
            if 'pdf' not in ctype and 'application/octet-stream' not in ctype and 'application/x-download' not in ctype:
                logging.warning(f"Unexpected content type {ctype} for URL: {url}")
                return None
            total=int(r.headers.get('Content-Length',0) or 0)
            with open(out_path,'wb') as f:
                if total>0:
                    for chunk in tqdm(r.iter_content(chunk_size=1<<16),total=total//(1<<16)+1):
                        if chunk: f.write(chunk)
                else:
                    for chunk in r.iter_content(chunk_size=1<<16):
                        if chunk: f.write(chunk)
        PdfReader(str(out_path))
        logging.info(f"Successfully downloaded PDF to: {out_path}")
        return out_path
    except Exception as e:
        logging.error(f"Exception while downloading {url}: {e}")
        if out_path.exists(): out_path.unlink()
        return None

def build_references_page(refs:list[tuple[str,str]], out_pdf:Path):
    """Render references page as a text PDF using ReportLab (no images).

    refs: list of (title, url) tuples
    """
    logging.info(f"Building references PDF with {len(refs)} items to {out_pdf}")
    c = canvas.Canvas(str(out_pdf), pagesize=A4)
    width, height = A4
    left = inch * 0.75
    y = height - inch * 0.8
    c.setFont('Helvetica-Bold', 16)
    c.drawString(left, y, 'References & External Links')
    y -= 24
    c.setFont('Helvetica', 10)
    for idx, (title, link) in enumerate(refs, start=1):
        line = f"{idx}. {title}: {link}"
        wrapped = tw.wrap(line, width=100)
        for part in wrapped:
            c.drawString(left, y, part)
            y -= 12
            if y < inch * 0.8:
                c.showPage()
                c.setFont('Helvetica', 10)
                y = height - inch * 0.8
        y -= 6
    c.save()


def strip_page_numbers(pdf_path:Path) -> Path:
    """Surgically remove page-number text objects near the bottom-right.

    Uses PyMuPDF (fitz) to inspect text spans and redact only those spans
    that look like page numbers (1-4 digits) positioned near the bottom-right
    of the page. If PyMuPDF is not installed, this function returns the
    original path unchanged.
    """
    if not HAVE_FITZ:
        logging.debug("PyMuPDF not available; skipping surgical page-number removal")
        return pdf_path

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        logging.warning(f"Failed to open PDF with PyMuPDF for surgical modification: {e}")
        return pdf_path

    digit_re = re.compile(r'^\s*\d{1,4}\s*$')
    modified_any = False
    removed = 0
    for page in doc:
        try:
            r = page.rect
            w, h = r.width, r.height
            # search region: bottom-right quadrant (customizable)
            search_box = fitz.Rect(w * 0.6, h * 0.82, w, h)

            txt = page.get_text('dict')
            page_modified = False
            for block in txt.get('blocks', []):
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        s = span.get('text', '')
                        if not s or not digit_re.match(s):
                            continue
                        bbox = span.get('bbox')
                        if not bbox or len(bbox) < 4:
                            continue
                        x0, y0, x1, y1 = bbox[0], bbox[1], bbox[2], bbox[3]
                        span_rect = fitz.Rect(x0, y0, x1, y1)
                        if search_box.contains(span_rect):
                            pad = max(1.0, min(w, h) * 0.005)
                            redact_rect = fitz.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
                            try:
                                page.add_redact_annot(redact_rect, fill=(1, 1, 1))
                                page_modified = True
                                removed += 1
                            except Exception:
                                continue
            if page_modified:
                modified_any = True
        except Exception:
            continue

    if modified_any:
        try:
            # apply redactions per-page (PyMuPDF Document may not expose apply_redactions)
            for p in doc:
                try:
                    p.apply_redactions()
                except Exception:
                    # some pages may not have redact annots; ignore
                    pass
            out_tmp = pdf_path.with_suffix('.nopagenum.pdf')
            doc.save(str(out_tmp), garbage=4, deflate=True)
            doc.close()
            try:
                pdf_path.unlink()
            except Exception:
                pass
            out_tmp.rename(pdf_path)
            logging.info(f"Removed {removed} page-number spans from: {pdf_path.name}")
            return pdf_path
        except Exception as e:
            logging.warning(f"Failed to apply redactions/save for {pdf_path}: {e}")
            try:
                doc.close()
            except Exception:
                pass
            return pdf_path
    else:
        try:
            doc.close()
        except Exception:
            pass
        return pdf_path


def build_toc_page(headings:list[str], out_pdf:Path):
    """Simple text TOC for cases where no heading->page mapping is available."""
    logging.info(f"Building simple text TOC with {len(headings)} headings to {out_pdf}")
    c = canvas.Canvas(str(out_pdf), pagesize=A4)
    width, height = A4
    left = inch * 0.75
    y = height - inch * 1.0
    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(width/2, y, 'Table of Contents')
    y -= 30
    c.setFont('Helvetica', 11)
    for idx, heading in enumerate(headings, start=1):
        line = f"{idx}. {heading}"
        wrapped = tw.wrap(line, width=100)
        for part in wrapped:
            c.drawString(left, y, part)
            y -= 14
            if y < inch:
                c.showPage()
                c.setFont('Helvetica', 11)
                y = height - inch
        y -= 6
    c.save()
    logging.info(f"Simple TOC text PDF saved to {out_pdf}")
def build_toc_page_with_numbers(headings_with_pages:list[tuple[str,int]], out_pdf:Path):
    """Create a clean text-based TOC PDF using ReportLab.

    Produces real text (selectable/searchable) instead of a raster image.
    """
    logging.info(f"Building numbered TOC (text PDF) with {len(headings_with_pages)} entries to {out_pdf}")
    c = canvas.Canvas(str(out_pdf), pagesize=A4)
    width, height = A4
    left = inch * 0.75
    right = width - inch * 0.75
    y = height - inch * 1.0

    # Title centered
    c.setFont('Helvetica-Bold', 20)
    c.drawCentredString(width/2, y, 'Table of Contents')
    y -= 30

    # content font
    c.setFont('Helvetica', 11)
    for heading, page in headings_with_pages:
        # section headers
        if re.match(r'^Part\b', heading, re.IGNORECASE) or heading.strip() == 'Appendix':
            c.setFont('Helvetica-Bold', 12)
            c.drawString(left, y, heading)
            c.setFont('Helvetica', 11)
            y -= 18
            continue

        # detect 'Chapter N' and strip label
        m = re.match(r'^Chapter\s*(\d+)[:\.]?\s*(.*)', heading, re.IGNORECASE)
        if m:
            label = f"{m.group(1)}. {m.group(2).strip()}"
            indent = 14
        else:
            m2 = re.match(r'^(Appendix\s+[A-Z])[:\s-]*(.*)', heading, re.IGNORECASE)
            if m2:
                label = f"{m2.group(1)} {m2.group(2).strip()}" if m2.group(2).strip() else m2.group(1)
                indent = 14
            else:
                label = heading
                indent = 0

        # Display the visible page number directly (no offset needed)
        page_text = str(page) if page and page>0 else ''
        c.drawString(left + indent, y, label)
        # dotted leader
        text_width = c.stringWidth(label, 'Helvetica', 11)
        page_w = c.stringWidth(page_text, 'Helvetica', 11)
        leader_x = left + indent + text_width + 6
        leader_w = right - leader_x - page_w - 6
        if leader_w > 0:
            num_dots = max(1, int(leader_w / c.stringWidth('.', 'Helvetica', 11)))
            c.drawString(leader_x, y, '.' * num_dots)
        if page_text:
            c.drawRightString(right, y, page_text)

        y -= 16
        if y < inch:
            c.showPage()
            c.setFont('Helvetica', 11)
            y = height - inch

    c.save()
    logging.info(f"Numbered TOC text PDF saved to {out_pdf}")


def visible_to_pdf_index(visible_page_num, visible_numbers_file):
    """Convert a visible page number to the actual PDF page index.
    
    visible_page_num: The visible page number (what users see)
    visible_numbers_file: Path to JSON file containing visible page number mapping
    
    Returns: 0-based PDF page index, or None if not found
    """
    try:
        import json
        logging.debug(f"Looking for visible page {visible_page_num} in {visible_numbers_file}")
        with open(visible_numbers_file, 'r') as f:
            visible_numbers = json.load(f)
        
        logging.debug(f"Loaded {len(visible_numbers)} visible numbers from file")
        
        # Find the PDF page index that corresponds to this visible page number
        for pdf_idx, visible_num in enumerate(visible_numbers):
            if visible_num == visible_page_num:
                logging.debug(f"Found visible page {visible_page_num} at PDF index {pdf_idx}")
                return pdf_idx
        
        logging.debug(f"Visible page {visible_page_num} not found in mapping")
        return None
    except Exception as e:
        logging.debug(f"Failed to convert visible page {visible_page_num}: {e}")
        return None


def add_toc_clickable_links(toc_pdf:Path, final_pdf:Path, heading_page_pairs:list[tuple[str,int]], toc_start:int=1):
    """Add internal GoTo link annotations to TOC entries in toc_pdf (which is
    embedded into final_pdf) so clicking TOC text jumps to the destination page.

    This function computes the layout positions using the same layout rules
    as build_toc_page_with_numbers and maps each entry to a rectangle on the
    corresponding TOC page, then inserts a pymupdf Link (LINK_GOTO) to the
    destination (final page index).
    """
    if not HAVE_FITZ:
        logging.debug("PyMuPDF not available; skipping TOC clickable links insertion")
        return
        
    logging.info(f"Adding clickable TOC links for {len(heading_page_pairs)} headings")
    logging.info(f"TOC PDF: {toc_pdf}")
    logging.info(f"Final PDF: {final_pdf}")
    
    try:
        # Open the TOC PDF and final PDF; we'll modify final_pdf in-place by
        # adding link annotations to its TOC pages which match toc_pdf pages.
        import fitz  # Import fitz locally to avoid scoping issues
        toc_doc = fitz.open(str(toc_pdf))
        final_doc = fitz.open(str(final_pdf))
        logging.info(f"Opened TOC PDF with {len(toc_doc)} pages")
        logging.info(f"Opened final PDF with {len(final_doc)} pages")
    except Exception as e:
        logging.warning(f"Failed to open PDFs for TOC link insertion: {e}")
        return

    # Layout constants - must match build_toc_page_with_numbers
    width, height = A4  # reportlab units in points
    left = inch * 0.75
    right = width - inch * 0.75
    start_y = height - inch * 1.0
    title_height = 30
    line_height = 16
    font_size = 11

    # Load visible page numbers for conversion
    workdir = final_pdf.parent / '_agentic_build'
    visible_numbers_file = workdir / '_visible_numbers.json'
    
    # Build a map of heading -> final page number (1-based)
    heading_map = {h: pg for (h, pg) in heading_page_pairs}

    # Build a list of (toc_page_index, rect, dest_page_index) for each entry
    entries = []
    y = start_y - title_height
    toc_page_idx = 0
    
    logging.info("Building TOC entry rectangles and destinations:")
    
    for heading, visible_page in heading_page_pairs:
        # account for part headings which consume vertical space but may not be links
        if re.match(r'^Part\b', heading, re.IGNORECASE) or heading.strip() == 'Appendix':
            y -= 18
            if y < inch:
                toc_page_idx += 1
                y = start_y
            continue

        # skip entries with no page
        if not visible_page or visible_page <= 0:
            y -= line_height
            if y < inch:
                toc_page_idx += 1
                y = start_y
            continue

        # Convert visible page number to PDF page index
        pdf_page_idx = visible_to_pdf_index(visible_page, visible_numbers_file)
        if pdf_page_idx is None:
            logging.debug(f"Could not convert visible page {visible_page} to PDF index for '{heading}'")
            y -= line_height
            if y < inch:
                toc_page_idx += 1
                y = start_y
            continue

        # compute label width to determine leader and page number placement
        from reportlab.pdfbase.pdfmetrics import stringWidth
        try:
            text_width = stringWidth(heading, 'Helvetica', font_size)
            page_text = str(visible_page)
            page_w = stringWidth(page_text, 'Helvetica', font_size)
        except Exception:
            text_width = 200
            page_w = 20

        indent = 14 if re.match(r'^Chapter\s*(\d+)', heading, re.IGNORECASE) else 0
        if re.match(r'^Appendix\s+[A-Z]', heading, re.IGNORECASE):
            indent = 14
            
        label_x = left + indent
        label_y = y
        
        # Convert ReportLab coordinates (bottom-left origin) to PyMuPDF coordinates (top-left origin)
        # ReportLab Y increases upward, PyMuPDF Y increases downward
        pymupdf_y = height - label_y  # Flip Y coordinate
        
        # Improved clickable area calculation for PyMuPDF coordinate system
        rect_x0 = label_x
        rect_x1 = right
        rect_y0 = pymupdf_y - font_size * 0.8  # slightly above text (in PyMuPDF coords)
        rect_y1 = pymupdf_y + font_size * 0.5  # slightly below text (in PyMuPDF coords)

        import fitz  # Import locally to avoid scoping issues
        entries.append((toc_page_idx, fitz.Rect(rect_x0, rect_y0, rect_x1, rect_y1), pdf_page_idx, heading, visible_page))
        logging.debug(f"Entry: '{heading}' -> visible_page={visible_page}, pdf_idx={pdf_page_idx}")

        y -= line_height
        if y < inch:
            toc_page_idx += 1
            y = start_y
    
    logging.info(f"Created {len(entries)} TOC link entries")

    # Insert link annotations into final_doc TOC pages
    links_added = 0
    for toc_page_idx, rect, pdf_dest_idx, heading, visible_page in entries:
        try:
            # final_doc pages are 0-based
            final_toc_page_idx = toc_start + toc_page_idx
            if final_toc_page_idx < 0 or final_toc_page_idx >= len(final_doc):
                logging.debug(f"TOC page {final_toc_page_idx} out of range for '{heading}'")
                continue
                
            if pdf_dest_idx < 0 or pdf_dest_idx >= len(final_doc):
                logging.debug(f"Destination page {pdf_dest_idx} out of range for '{heading}'")
                continue
                
            page = final_doc[final_toc_page_idx]
            
            try:
                # Create a link using 0-based page indices (PyMuPDF standard)
                # The pdf_dest_idx is already 0-based, so use it directly
                import fitz  # Import locally to avoid scoping issues
                link_dict = {
                    "kind": fitz.LINK_GOTO,
                    "page": pdf_dest_idx,  # Use 0-based index directly
                    "from": rect
                }
                page.insert_link(link_dict)
                links_added += 1
                logging.info(f"HYPERLINK CREATED: '{heading}' -> PDF index {pdf_dest_idx} (visible page {visible_page})")
                logging.debug(f"HYPERLINK RECT: {rect}")
                logging.debug(f"HYPERLINK DICT: {link_dict}")
            except Exception as e:
                logging.warning(f"Failed to add TOC link for '{heading}': {e}")
            
        except Exception as e:
            logging.debug(f"Failed to add TOC link for '{heading}': {e}")

    logging.info(f"Successfully added {links_added} clickable TOC links")

    try:
        logging.info(f"Saving final PDF with TOC links to: {final_pdf}")
        final_doc.saveIncr()
        logging.info("Successfully saved final PDF with incremental update")
    except Exception:
        try:
            backup_path = final_pdf.with_suffix('.linked.pdf')
            final_doc.save(str(backup_path))
            logging.warning(f"Failed incremental save, saved to backup: {backup_path}")
        except Exception as e:
            logging.warning(f"Failed to save final PDF with TOC links: {e}")
    
    try:
        toc_doc.close()
        final_doc.close()
        logging.info("Closed PDF documents")
    except Exception:
        pass


def map_headings_to_pages(headings:list[str], merged_paths:list[Path], start_page_offset:int=0):
    """Map headings to absolute page numbers based on merged_paths.

    merged_paths should reflect the order of PDFs as they will appear
    without the TOC inserted. This function returns a list of (heading,page)
    where page is the 1-based page number in the final merged PDF when the
    TOC is NOT yet inserted. The caller can then insert TOC and adjust pages.
    """
    logging.info(f"Mapping {len(headings)} headings to pages based on merged paths")
    # Build a map: merged_paths index -> starting absolute page number
    start_pages = []
    current_page = start_page_offset + 1  # cover usually at page 1
    for p in merged_paths:
        start_pages.append(current_page)
        try:
            reader = PdfReader(str(p))
            page_count = len(reader.pages)
        except Exception:
            page_count = 1
        current_page += page_count

    # Assume a simple 1:1 mapping from headings (excluding 'Part' markers)
    # to PDFs in merged_paths starting after cover. Build mapping by iterating
    # headings and assigning them to successive PDFs (skipping part markers).
    parts = ["Part One", "Part Two", "Part Three", "Part Four", "Appendix"]
    result = []
    pdf_idx = 1  # merged_paths[0] is cover; pdf_idx points to first content PDF
    for h in headings:
        if h in parts:
            # no specific page for part headings - map to 0
            result.append((h, 0))
            continue
        # find next PDF that is not the TOC placeholder (we assume TOC not present)
        if pdf_idx >= len(merged_paths):
            result.append((h, 0))
            continue
        page_num = start_pages[pdf_idx]
        result.append((h, page_num))
        # advance pdf_idx by 1 to map next heading to next PDF
        pdf_idx += 1

    logging.info(f"Completed mapping of headings to pages")
    return result


def merge_pdfs(paths:list[Path], out_path:Path, add_bookmarks:bool=False, bookmark_titles:list[str]|None=None):
    merger=PdfWriter()
    page_indices = []
    for p in paths:
        reader = PdfReader(str(p))
        start_page = len(merger.pages)
        for page in reader.pages:
            merger.add_page(page)
        end_page = len(merger.pages) - 1
        page_indices.append((start_page, end_page))
    
    # bookmark_titles can be either a list of strings (old behavior) or a
    # list of (title,page) pairs. If provided and add_bookmarks=True, create
    # outline items pointing to the correct page.
    if add_bookmarks and bookmark_titles:
        # build a map of merged page index -> title
        if all(isinstance(t, (list,tuple)) and len(t)==2 for t in bookmark_titles):
            # user supplied explicit (title,page) pairs
            for title, pg in bookmark_titles:
                try:
                    # PdfWriter uses 0-based page indices
                    merger.add_outline_item(title, pg-1)
                except Exception:
                    logging.debug(f"Failed to add explicit bookmark for {title} -> {pg}")
        else:
            for i, (start_page, end_page) in enumerate(page_indices):
                if i < len(bookmark_titles):
                    title = bookmark_titles[i]
                    try:
                        merger.add_outline_item(title, start_page)
                    except Exception:
                        logging.debug(f"Failed to add bookmark for {title} at {start_page}")
    
    merger.write(str(out_path))
    merger.close()


# Note: visible page number computation and stamping moved to external
# script `stamp_page_numbers.py`. This keeps the build script simpler and
# allows running the stamping step independently.


def read_manifest(manifest:Path):
    rows=[]
    with open(manifest,newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows

def main():
    logging.info("Starting the book compilation process.")
    ap=argparse.ArgumentParser(description='Compile Agentic Design Patterns book')
    ap.add_argument('--index-pdf', required=True)
    ap.add_argument('--cover', required=True)
    ap.add_argument('--out', default='Agentic_Design_Patterns_compiled.pdf')
    ap.add_argument('--workdir', default='_agentic_build')
    ap.add_argument('--manifest', default=None)
    ap.add_argument('--add-toc', action='store_true')
    ap.add_argument('--skip-index-body', action='store_true')
    args=ap.parse_args()
    logging.info(f"Parsed arguments: index_pdf={args.index_pdf}, cover={args.cover}, out={args.out}, workdir={args.workdir}")
    index_pdf=Path(args.index_pdf).resolve()
    cover=Path(args.cover).resolve()
    out_pdf=Path(args.out).resolve()
    workdir=Path(args.workdir).resolve()
    ensure_dir(workdir)
    logging.info(f"Working directory: {workdir}")
    # make cover pdf
    cover_pdf=workdir/'00_cover.pdf'
    if cover.suffix.lower()=='.pdf': shutil.copy(cover,cover_pdf)
    else: pil_cover_to_pdf(cover,cover_pdf)
    logging.info("Cover PDF created.")
    # extract links
    links=extract_pdf_links(index_pdf)
    logging.info(f"Extracted {len(links)} links from index PDF.")
    
    # extract headings for table of contents
    headings=extract_pdf_headings(index_pdf)
    logging.info(f"Extracted {len(headings)} headings for table of contents.")
    if headings:
        logging.info(f"Sample headings: {headings[:3]}")  # Log first 3 headings
    else:
        logging.warning("No headings extracted from index PDF - TOC will not be created")
    
    # dedupe
    seen=set(); link_list=[]
    for u in links:
        if u not in seen:
            link_list.append(u); seen.add(u)
    logging.info(f"After deduplication: {len(link_list)} unique links.")
    # manifest
    manifest_rows=[]
    if args.manifest:
        manifest_rows=read_manifest(Path(args.manifest))
    downloads_dir=workdir/'downloads'
    ensure_dir(downloads_dir)
    merged_paths=[cover_pdf]
    titles=['Cover']
    
    # Defer TOC creation until after downloads so we can map headings to correct pages
    toc_pdf=workdir/'01_toc.pdf'
    
    # Note: index.pdf is not included to avoid duplicate cover content
    logging.info("Skipping index.pdf inclusion to avoid duplicate cover content")
    queue=[]
    if manifest_rows:
        man_sorted=sorted(manifest_rows, key=lambda r:r.get('order',''))
        for r in man_sorted:
            queue.append((r.get('title',''), r.get('url','').strip()))
    manifested={r.get('url','').strip() for r in manifest_rows} if manifest_rows else set()
    for u in link_list:
        if u not in manifested:
            queue.append(('', u))
    session=requests.Session()
    failed=[]; referenced_only=[]
    drive_folders=[]
    logging.info("Starting download process for links.")
    for title,url in queue:
        if not url: continue
        logging.info(f"Processing URL: {url}")
        folder_id=is_drive_folder(url)
        if folder_id:
            drive_folders.append((title or f"Drive Folder {folder_id}", url))
            logging.info(f"Skipped Drive folder: {url} (added to references)")
            continue
        pdf_path=fetch_url_to_pdf(url, downloads_dir, session)
        if pdf_path:
            # Attempt to strip visible page numbers (headers/footers) from downloaded PDF
            try:
                pdf_path = strip_page_numbers(pdf_path)
            except Exception:
                logging.debug(f"Page number stripping failed or skipped for {pdf_path}")

            merged_paths.append(pdf_path)
            titles.append(title or pdf_path.stem)
            logging.info(f"Downloaded PDF: {pdf_path}")
        else:
            referenced_only.append((title or "Unknown", url))
            logging.error(f"Failed to download PDF from: {url}")
    logging.info("Download process completed.")
    if referenced_only or drive_folders:
        all_refs = referenced_only + drive_folders
        refs_pdf=workdir/'zzz_references.pdf'
        build_references_page(all_refs,refs_pdf)
        merged_paths.append(refs_pdf)
        titles.append('References & External Links')
        logging.info(f"Created references page with {len(all_refs)} unresolved links and drive folders.")
    
    # Now build numbered TOC by mapping headings to pages. We perform a
    # two-pass approach: first compute page offsets from the current
    # merged_paths (cover + downloads + references) WITHOUT the TOC, map
    # headings to those page numbers, then render the TOC and insert it at
    # index 1. After insertion, all pages after the TOC shift by the TOC's
    # page count; we adjust the page numbers used for bookmarks accordingly.
    if headings:
        logging.info("Merging temporarily (no TOC) to compute visible page numbers")
        temp_no_toc = workdir/'_merged_notoc.pdf'
        merge_pdfs(merged_paths, temp_no_toc, add_bookmarks=False, bookmark_titles=None)

        # Compute visible page numbers for the merged PDF (ignoring blank pages)
        try:
            import subprocess, json
            dump_file = workdir/'_visible_numbers.json'
            script = Path(__file__).parent / 'stamp_page_numbers.py'
            subprocess.run(['python3', str(script), str(temp_no_toc), '--dump-json', str(dump_file)], check=True)
            with open(dump_file,'r',encoding='utf-8') as f:
                visible_numbers = json.load(f)
        except Exception as e:
            logging.warning(f"Failed to compute visible page numbers via external script: {e}")
            # fallback: mark all pages as visible sequentially
            tmp_reader = PdfReader(str(temp_no_toc))
            visible_numbers = list(range(1, len(tmp_reader.pages)+1))

        # Map headings to page indices based on merged_paths (pre-TOC)
        pre_toc_pairs = map_headings_to_pages(headings, merged_paths, start_page_offset=0)

        # Convert pre_toc_pairs to visible page numbers by looking up the first
        # non-None visible number at or after the target page.
        mapped = []
        tmp_reader = PdfReader(str(temp_no_toc))
        total_pages = len(tmp_reader.pages)
        for h, pg in pre_toc_pairs:
            if not pg or pg < 1 or pg > total_pages:
                mapped.append((h, 0))
                continue
            # search from pg-1 index forward for a visible number
            vis = None
            for i in range(pg-1, total_pages):
                if visible_numbers[i] is not None:
                    vis = visible_numbers[i]
                    break
            mapped.append((h, vis or 0))

        # Build TOC using the visible PDF-wise page numbers
        build_toc_page_with_numbers(mapped, toc_pdf)
        try:
            toc_reader = PdfReader(str(toc_pdf))
            toc_page_count = len(toc_reader.pages)
        except Exception:
            toc_page_count = 1

        # Insert TOC after cover (index 1)
        merged_paths.insert(1, toc_pdf)
        titles.insert(1, 'Table of Contents')
        logging.info(f"Inserted TOC ({toc_page_count} pages) into merged paths")

        # Adjust heading pairs by adding toc page count where appropriate
        heading_page_pairs = []
        for h, pg in mapped:
            if pg and pg > 0:
                heading_page_pairs.append((h, pg + toc_page_count))
            else:
                heading_page_pairs.append((h, pg))
        logging.info("Built TOC mapped to visible PDF page numbers")
    else:
        logging.warning("No headings available to build numbered TOC; inserting basic TOC")
        basic_headings = ["Agentic Design Patterns", "Introduction", "Core Concepts", "Implementation Guide"]
        build_toc_page(basic_headings, toc_pdf)
        merged_paths.insert(1, toc_pdf)
        titles.insert(1, 'Table of Contents')
    # If add_toc requested and we have heading->page mappings, create explicit
    # (title,page) bookmark pairs so the PDF outline links to TOC pages.
    # Build bookmark argument: if we computed heading_page_pairs, prefer explicit (title,page)
    bookmark_arg = titles
    add_bookmarks_flag = args.add_toc
    if headings:
        try:
            explicit = [(h, pg) for (h, pg) in heading_page_pairs if pg and pg>0]
            if explicit:
                bookmark_arg = explicit
                add_bookmarks_flag = True
                logging.info(f"Adding {len(bookmark_arg)} explicit bookmarks from TOC headings")
        except Exception:
            bookmark_arg = titles

    merge_pdfs(merged_paths, out_pdf, add_bookmarks=add_bookmarks_flag, bookmark_titles=bookmark_arg)
    logging.info(f"Merged {len(merged_paths)} PDFs: {[p.name for p in merged_paths]}")
    # If we computed visible_numbers earlier (temp_no_toc), stamp final PDF
    try:
        if headings:
            # visible_numbers corresponds to merged without TOC; we need to
            # insert None for TOC pages at the front so that stamping aligns
            shifted = []
            # first page is cover (usually visible_numbers[0])
            # TOC pages inserted after cover: shift all visible numbers by toc_page_count
            for _ in range(toc_page_count + 1):
                shifted.append(None)
            # append the rest of visible_numbers
            shifted.extend(visible_numbers)
            # Trim or extend shifted to match final page count
            final_reader = PdfReader(str(out_pdf))
            final_count = len(final_reader.pages)
            if len(shifted) < final_count:
                shifted.extend([None] * (final_count - len(shifted)))
            elif len(shifted) > final_count:
                shifted = shifted[:final_count]

            # call external script to stamp page numbers
            try:
                import subprocess
                script = Path(__file__).parent / 'stamp_page_numbers.py'
                args = ['python3', str(script), str(out_pdf)]
                subprocess.run(args, check=True)
                logging.info(f"Stamped visible page numbers via script for: {out_pdf}")
            except Exception as e:
                logging.warning(f"Failed to stamp page numbers via external script: {e}")
            # Attempt to add clickable TOC links if PyMuPDF is available
            try:
                if HAVE_FITZ and headings and 'heading_page_pairs' in locals():
                    logging.info(f"Adding clickable TOC links for {len(heading_page_pairs)} headings")
                    add_toc_clickable_links(toc_pdf, out_pdf, heading_page_pairs, toc_start=1)
                    logging.info("Inserted clickable TOC text links into final PDF (best-effort)")
            except Exception as e:
                logging.debug(f"Failed to insert clickable TOC links: {e}")
    except Exception as e:
        logging.warning(f"Failed to stamp page numbers: {e}")

    logging.info(f"Compiled book written to {out_pdf}")
    print('Compiled book written to',out_pdf)

if __name__=='__main__':
    main()
