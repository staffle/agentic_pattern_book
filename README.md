# Agentic Design Patterns Book

A Python tool for compiling academic papers and documents into a cohesive book format with automatic PDF processing, link extraction, and document merging.

## Overview

This project takes a preprint PDF (like an index or table of contents) with embedded links to Google Docs, Sheets, Slides, and other online documents, then automatically:

- Extracts URLs from PDF annotations and text
- Downloads and converts linked documents to PDF format
- Merges all documents with a custom cover
- Generates a table of contents
- Creates a references page for unresolved links

## Features

- **Automatic Link Extraction**: Finds URLs in PDF annotations and plain text
- **Google Workspace Integration**: Converts Google Docs/Sheets/Slides to PDF
- **Public Drive Folder Scraping**: Downloads documents from shared Google Drive folders
- **PDF Processing**: Merges multiple PDFs with proper page numbering
- **Table of Contents**: Optional TOC generation
- **Cover Integration**: Supports JPG, PNG, or PDF covers
- **Reference Management**: Lists unresolved links in a references section

## Quick Start

1. **Set up environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Prepare your files**:
   - Place your index PDF and cover image in the project root
   - Ensure your index PDF contains links to the documents you want to compile

3. **Build the book**:
   ```bash
   chmod +x make.sh
   ./make.sh
   ```

   Or run directly:
   ```bash
   python3 src/build_book.py index.pdf
   ```

   With custom configuration:
   ```bash
   python3 src/build_book.py index.pdf --book-config agentic_design_patterns
   ```

## Command Line Options

- `--index-pdf`: Path to the main PDF containing links to other documents
- `--cover`: Cover image (JPG, PNG) or PDF file
- `--out`: Output path for the compiled book
- `--workdir`: Working directory for temporary files (default: `_agentic_build`)
- `--book-config`: Book configuration to use (default: `agentic_design_patterns`)
- `--add-toc`: Generate a table of contents

## Book Configurations

The build system supports multiple book configurations through `src/book_config.py`. Each configuration contains:

- Book name and output filename
- Working directory name
- Predefined table of contents headings
- Other book-specific settings

### Available Configurations

- `agentic_design_patterns`: Configuration for the Agentic Design Patterns book

### Adding New Configurations

To add a new book configuration:

1. Open `src/book_config.py`
2. Create a new configuration dictionary:
   ```python
   NEW_BOOK_CONFIG = {
       'name': 'Your Book Name',
       'output_filename': 'Your_Book_compiled.pdf', 
       'workdir': '_your_build',
       'predefined_headings': [
           'Chapter 1: Introduction',
           'Chapter 2: Advanced Topics',
           # Add your TOC headings here
       ]
   }
   ```
3. Add it to the `BOOK_CONFIGS` dictionary:
   ```python
   BOOK_CONFIGS = {
       'agentic_design_patterns': AGENTIC_DESIGN_PATTERNS_CONFIG,
       'your_book': NEW_BOOK_CONFIG,
   }
   ```
4. Use it: `python src/build_book.py index.pdf --book-config your_book`

## Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt`:
  - pypdf
  - requests
  - beautifulsoup4
  - pillow
  - tqdm
  - reportlab
  - PyMuPDF (optional, for enhanced PDF processing)

## File Structure

```
├── src/
│   ├── build_book.py       # Main compilation script
│   ├── book_config.py      # Book configuration settings
│   └── stamp_page_numbers.py  # Page numbering utility
├── _agentic_build/         # Working directory (auto-generated)
├── requirements.txt        # Python dependencies
├── make.sh                # Build script
├── index.pdf              # Your index/TOC PDF
├── cover.jpeg             # Cover image
└── README.md              # This file
```

## How It Works

1. **URL Extraction**: Scans the index PDF for hyperlinks in annotations and text
2. **Link Processing**: Normalizes URLs, especially Google Workspace links
3. **Document Download**: Fetches linked documents and converts to PDF
4. **PDF Assembly**: Merges cover, table of contents, downloaded documents, and references
5. **Output Generation**: Creates the final compiled book with proper page numbering

## Supported Link Types

- Google Docs (automatically converted to PDF)
- Google Sheets (exported as PDF)
- Google Slides (exported as PDF)
- Public Google Drive folders (recursively scraped)
- Direct PDF links
- Other web pages (converted to PDF when possible)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Troubleshooting

- **Missing links**: Check that URLs in your index PDF are properly formatted
- **Download failures**: Ensure linked documents are publicly accessible
- **PDF merge issues**: Verify that all source PDFs are valid and not corrupted
- **Memory issues**: For large documents, consider processing in smaller batches

## Support

If you encounter issues or have questions, please open an issue on the repository.
