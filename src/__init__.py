"""
PDF Layout Analysis Engine

A comprehensive system for extracting structured content from PDF documents using
advanced computer vision and machine learning techniques.

This package provides:
- Multi-column layout detection
- Text block extraction and grouping  
- Figure and table recognition
- Caption linking and reading order determination
- Robust error handling for various PDF formats

Example:
    >>> from pdf_layout_engine import process_pdf
    >>> result = process_pdf("document.pdf", "output/")
    >>> print(f"Found {len(result['figures'])} figures and {len(result['tables'])} tables")

Modules:
- pdf_io: PDF loading, rendering, coordinate conversion
- columns: Column detection using whitespace valley analysis
- text_blocks: Text extraction and paragraph grouping
- figures: Figure detection using vector clustering and image XObjects
- tables: Table detection using ruled and borderless methods
- captions: Caption detection and linking to figures/tables
- order: Reading order and section assembly
- export: JSON/CSV output and debug overlays
- runner: CLI orchestrator
"""

__version__ = "1.0.0"
__author__ = "PDF Layout Analysis Team"
__email__ = "team@pdf-layout-engine.org"
__license__ = "MIT"

# Import main functions for easy access
from .core.pipeline_processor import process_pdf, process_page
from .core.pdf_handler import load_pdf_page_data, render_page
from .detection.column_detector import detect_columns
from .detection.text_detector import extract_text_blocks, group_lines_into_paragraphs
from .detection.figure_detector import detect_figures
from .detection.table_detector import extract_tables
from .processing.caption_processor import link_captions
from .processing.content_organizer import assemble_sections
from .core.output_manager import write_page_outputs

__all__ = [
    'process_pdf',
    'process_page', 
    'load_pdf_page_data',
    'render_page',
    'detect_columns',
    'extract_text_blocks',
    'group_lines_into_paragraphs',
    'detect_figures',
    'extract_tables',
    'link_captions',
    'assemble_sections',
    'write_page_outputs'
]
