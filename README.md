# PDF Extraction Pipeline

A comprehensive PDF extraction system that analyzes document structure, extracts text, figures, tables, and captions, and outputs structured data in JSON format.

## Features

- **Column Detection**: Uses whitespace valley analysis to detect multi-column layouts
- **Text Extraction**: Extracts and groups text into paragraphs with heading detection
- **Figure Detection**: Detects figures using vector clustering and image XObjects
- **Table Detection**: Supports both ruled and borderless table detection
- **Caption Linking**: Automatically links captions to figures and tables
- **Reading Order**: Assembles content into logical sections with proper reading order
- **Structured Output**: Exports data in JSON format with cropped images and CSV tables

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Optional: Install OCR for scanned documents:
```bash
# For PaddleOCR
pip install PaddleOCR

# OR for Tesseract
pip install pytesseract
```

## Usage

### Command Line Interface

```bash
# Process entire PDF
python -m src.runner input.pdf -o outputs

# Process specific pages
python -m src.runner input.pdf -o outputs -p "1,3,5-7"

# Generate debug overlays
python -m src.runner input.pdf -o outputs --debug

# Set logging level
python -m src.runner input.pdf -o outputs --log-level DEBUG
```

### Python API

```python
from src import process_pdf, run_single_page

# Process entire PDF
result = process_pdf("input.pdf", "outputs", debug=True)

# Process single page
page_data = run_single_page("input.pdf", 0, "outputs", debug=True)
```

## Output Format

The pipeline generates the following outputs per page:

### JSON Structure
```json
{
  "page_size": {"pt": [w,h], "px": [W,H], "dpi": 600},
  "columns": [{"x0":..,"x1":..}],
  "title": "…",
  "sections": [{"heading":"…","paragraphs":["…","…"]}],
  "figures": [{"bbox_px":[x0,y0,x1,y1],"image":"page_1_fig_1.png","caption":"…","source":"vector|image|mixed"}],
  "tables": [{"bbox_px":[...], "image":"page_1_table_1.png", "csv":"page_1_table_1.csv", "cells":[{"r":0,"c":0,"text":"…","bbox_px":[...]}], "caption":"…"}],
  "captions": [{"bbox_px":[...], "text":"…"}]
}
```

### Files Generated
- `page_N.json` - Structured layout data
- `page_N_fig_K.png` - Cropped figure images
- `page_N_table_K.png` - Cropped table images
- `page_N_table_K.csv` - Table data in CSV format
- `page_N_overlay.png` - Debug overlay (if --debug flag used)
- `page_N_audit.json` - Processing audit log
- `summary.json` - Overall processing summary

## Architecture

The pipeline consists of 9 main modules:

1. **pdf_io.py** - PDF loading, rendering, coordinate conversion
2. **columns.py** - Whitespace valley detection for column layout
3. **text_blocks.py** - Text extraction and paragraph grouping
4. **figures.py** - Vector clustering and image detection
5. **tables.py** - Ruled and borderless table detection
6. **captions.py** - Caption linking to figures/tables
7. **order.py** - Reading order and section assembly
8. **export.py** - JSON/CSV output and debug overlays
9. **runner.py** - CLI orchestrator

## Pipeline Steps

1. **Load & Preflight**: Open PDF, extract text/drawings/images, render at 600 DPI
2. **Column Detection**: Analyze whitespace valleys to detect column boundaries
3. **Text Blocks**: Extract text spans, group into lines and paragraphs
4. **Figure Detection**: Use DBSCAN clustering on vector drawings + image XObjects
5. **Table Detection**: Hough line detection for ruled tables, text alignment for borderless
6. **Caption Linking**: Match captions to figures/tables using proximity and patterns
7. **Section Assembly**: Group content into sections based on headings
8. **Reading Order**: Sort elements by position (top-to-bottom, left-to-right)
9. **Export**: Generate JSON, images, CSV, and debug overlays

## Configuration

Key constants can be adjusted in each module:

- `DPI_PAGE = 600` - Page rendering DPI
- `DBSCAN_EPS = 12` - Figure clustering epsilon
- `NMS_IOU = 0.5` - Non-maximum suppression threshold
- `CAPTION_BAND_FACTOR = 1.2` - Caption search band multiplier

## Testing

Run the test script to verify installation:

```bash
python test_pipeline.py
```

## Dependencies

- PyMuPDF (fitz) - PDF parsing and rendering
- OpenCV - Image processing and computer vision
- NumPy/Pillow - Image handling
- Scikit-learn - DBSCAN clustering
- Optional: PaddleOCR or Tesseract for OCR

## License

This project is provided as-is for research and development purposes.