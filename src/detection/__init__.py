"""
Detection modules for identifying different content types in PDFs.
Contains algorithms for detecting figures, tables, text blocks, and columns.
"""

from .figure_detector import detect_figures, crop_figure_image
from .table_detector import Table, extract_tables
from .text_detector import extract_text_blocks, group_lines_into_paragraphs, detect_headings
from .column_detector import detect_columns

__all__ = [
    'detect_figures',
    'crop_figure_image',
    'Table',
    'extract_tables',
    'extract_text_blocks',
    'group_lines_into_paragraphs', 
    'detect_headings',
    'detect_columns'
]
