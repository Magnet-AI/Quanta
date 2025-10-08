# PDF Extraction Pipeline - Source Code Organization

This directory contains the organized source code for the PDF extraction pipeline, structured into logical modules for better maintainability and clarity.

## Directory Structure

```
src/
├── core/                           # Core functionality
│   ├── __init__.py
│   ├── pipeline_processor.py      # Main processing pipeline orchestrator
│   ├── pdf_handler.py             # PDF input/output operations
│   └── output_manager.py          # Output generation and file writing
│
├── detection/                     # Content detection algorithms
│   ├── __init__.py
│   ├── figure_detector.py         # Figure/image detection and processing
│   ├── table_detector.py          # Table detection and processing
│   ├── text_detector.py           # Text block extraction and analysis
│   └── column_detector.py         # Column layout detection
│
├── extraction/                    # External service integrations
│   ├── __init__.py
│   ├── mistral_service.py         # Mistral OCR API integration
│   └── content_extractor.py       # Content extraction approaches
│
├── processing/                    # Post-processing modules
│   ├── __init__.py
│   ├── caption_processor.py       # Caption linking and processing
│   └── content_organizer.py       # Content ordering and section assembly
│
└── utils/                         # Utility functions and helpers
    ├── __init__.py
    └── ml_models.py               # ML models for table processing
```

## Module Descriptions

### Core (`core/`)
- **`pipeline_processor.py`**: Main pipeline orchestrator that coordinates all processing steps
- **`pdf_handler.py`**: Handles PDF loading, page extraction, and basic PDF operations
- **`output_manager.py`**: Manages output generation, file writing, and summary reports

### Detection (`detection/`)
- **`figure_detector.py`**: Detects and extracts figures/images using custom algorithms
- **`table_detector.py`**: Table detection and CSV generation (uses Mistral OCR data)
- **`text_detector.py`**: Text extraction, paragraph grouping, and heading detection
- **`column_detector.py`**: Multi-column layout detection and analysis

### Extraction (`extraction/`)
- **`mistral_service.py`**: Integration with Mistral OCR API for table and text extraction
- **`content_extractor.py`**: Content extraction approaches combining custom and external services

### Processing (`processing/`)
- **`caption_processor.py`**: Links captions to figures and tables
- **`content_organizer.py`**: Assembles content into logical sections and determines reading order

### Utils (`utils/`)
- **`ml_models.py`**: Machine learning models and utilities for table processing

## Key Features

- **Modular Design**: Each module has a specific responsibility
- **Clean Imports**: Well-organized import structure with `__init__.py` files
- **Hybrid Approach**: Combines custom algorithms (for figures) with Mistral OCR (for tables/text)
- **Page-Based Output**: Organizes all content by page in separate folders
- **CSV-Only Tables**: Tables are extracted as CSV files without PNG images

## Usage

The main entry point is through `main.py` which imports from `core.runner`. The pipeline processes PDFs and outputs organized content in page-specific folders.

## Dependencies

- Custom detection algorithms for figures and layout
- Mistral OCR API for table and text extraction
- OpenCV for image processing
- PyMuPDF for PDF operations
