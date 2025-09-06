# PaperStitch

A powerful tool for compiling multi-document publications by following links in PDF files. PaperStitch automatically downloads linked documents (especially Google Docs), converts them to PDFs, and weaves them together into a single, professionally formatted book with clickable table of contents.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/staffle/paperstitch.git
cd paperstitch

# Run the setup and build script
./make.sh
```

## ✨ Features

- **Link Following**: Automatically extracts and follows links from your index PDF
- **Google Docs Integration**: Seamlessly downloads and converts Google Docs to PDF
- **Smart Compilation**: Merges multiple documents while preserving formatting
- **Clickable TOC**: Generates interactive table of contents with working hyperlinks
- **Page Numbering**: Adds consistent page numbers throughout the compiled document
- **Configurable**: Easy-to-customize book configurations for different projects
- **Professional Output**: Creates publication-ready PDFs with proper formatting

## 📋 Requirements

- Python 3.7+
- Internet connection (for downloading linked documents)
- Dependencies listed in `requirements.txt`

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/staffle/paperstitch.git
   cd paperstitch
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare your files**:
   - Place your main PDF file (with links) in the root directory
   - Add a cover image file (JPEG, PNG, or PDF)

## 📖 Usage

### Basic Usage

```bash
python src/build_book.py index.pdf
```

### Advanced Usage with All Options

```bash
python src/build_book.py \
  --index-pdf "your_index.pdf" \
  --cover "your_cover.jpg" \
  --out "output/Your_Compiled_Book.pdf" \
  --workdir "_build" \
  --book-config "your_config_name" \
  --add-toc
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--index-pdf` | Path to your main PDF with links | Required |
| `--cover` | Cover image file (jpg/png/pdf) | None |
| `--out` | Output path for compiled PDF | `compiled_book.pdf` |
| `--workdir` | Working directory for temporary files | `_build` |
| `--book-config` | Book configuration to use | `default` |
| `--add-toc` | Add clickable table of contents | False |

### Using the Convenience Script

The `make.sh` script provides a quick way to build with common settings:

```bash
./make.sh
```

This script will:
1. Create a virtual environment
2. Install dependencies
3. Build your book with predefined settings

## 📁 File Structure

```
paperstitch/
├── src/
│   ├── build_book.py          # Main compilation script
│   ├── book_config.py         # Book configuration settings
│   └── stamp_page_numbers.py  # Page numbering utility
├── requirements.txt           # Python dependencies
├── make.sh                   # Convenience build script
├── README.md                 # This file
├── .gitignore               # Git ignore rules
├── index.pdf                # Your main PDF (place here)
├── cover.jpeg              # Your cover image (place here)
├── _build/                 # Working directory (auto-created)
└── output/                 # Compiled books output here
```

## ⚙️ Configuration

PaperStitch uses a configuration system to handle different book projects. Configurations are defined in `src/book_config.py`.

### Current Configurations

- **`agentic_design_patterns`**: Default configuration for the Agentic Design Patterns book
- **`default`**: Basic configuration for general use

### Adding a New Book Configuration

1. Open `src/book_config.py`
2. Add your configuration dictionary:
   ```python
   YOUR_BOOK_CONFIG = {
       "predefined_toc_headings": [
           "Chapter 1: Introduction",
           "Chapter 2: Your Content",
           # ... add your headings
       ]
   }
   ```
3. Register it in `BOOK_CONFIGS`:
   ```python
   BOOK_CONFIGS = {
       "your_book": YOUR_BOOK_CONFIG,
       # ... existing configs
   }
   ```
4. Use it with: `--book-config your_book`

## 🔧 How It Works

1. **Link Extraction**: Scans your index PDF for hyperlinks
2. **Document Discovery**: Identifies Google Docs and other supported document types
3. **Download & Convert**: Automatically downloads and converts documents to PDF
4. **Page Processing**: Adds consistent page numbering across all documents
5. **Smart Merging**: Combines all PDFs while maintaining proper page flow
6. **TOC Generation**: Creates clickable table of contents based on document structure
7. **Final Assembly**: Produces a single, professional PDF with cover and navigation

## 📝 Supported Link Types

- **Google Docs**: Automatically detected and converted
- **Direct PDF links**: Downloaded and included
- **Other document formats**: Basic support for various online documents

## 🐛 Troubleshooting

### Common Issues

**"No module named 'requests'"**
```bash
pip install -r requirements.txt
```

**"Can't open file 'build_book.py'"**
```bash
# Make sure you're running from the project root
python src/build_book.py --help
```

**"Permission denied" on make.sh**
```bash
chmod +x make.sh
```

**Links not working in output PDF**
- Ensure you used the `--add-toc` flag
- Check that your index PDF contains valid hyperlinks
- Verify the working directory contains `_visible_numbers.json`

### Debug Mode

For troubleshooting, you can check the working directory contents:
```bash
ls -la _build/  # Check downloaded files
cat _build/_visible_numbers.json  # Check page mapping
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source. Please check the license file for details.

## 🎯 Use Cases

- **Academic Papers**: Compile research papers with references
- **Technical Documentation**: Merge multiple technical documents
- **Book Publishing**: Create professional books from distributed content
- **Report Generation**: Combine multiple reports into single publications
- **Content Aggregation**: Stitch together content from various sources

---

**PaperStitch** - Weaving documents together, one link at a time. 🧵📄
