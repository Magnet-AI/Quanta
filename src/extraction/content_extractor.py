"""
Hybrid processor that combines:
- Mistral OCR for tables and text extraction
- Custom algorithm for figure/image detection
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from .mistral_ocr import MistralOCR, create_mistral_table
from .figures import detect_figures
from .text_blocks import TextBlock
from .tables import Table

class HybridProcessor:
    """Hybrid processor combining Mistral OCR and custom algorithms."""
    
    def __init__(self):
        self.mistral_ocr = MistralOCR()
    
    def process_page(self, pdf_path: str, page_number: int, page_image: np.ndarray, 
                    text_blocks: List[TextBlock], columns: List[Tuple[int, int]], 
                    page_width: int, page_height: int) -> Dict[str, Any]:
        """
        Process a single page using hybrid approach.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number
            page_image: Page image as numpy array
            text_blocks: Text blocks from custom extraction
            columns: Column boundaries
            page_width: Page width in pixels
            page_height: Page height in pixels
            
        Returns:
            Dictionary containing extracted content
        """
        logging.info(f"Processing page {page_number} with hybrid approach")
        
        # Use Mistral OCR for tables and text
        mistral_content = self.mistral_ocr.process_pdf_page(pdf_path, page_number)
        
        # Use custom algorithm for figures
        figures = detect_figures(page_image, text_blocks, page_width, page_height)
        
        # Convert Mistral tables to our Table format
        mistral_tables = []
        for table_data in mistral_content.get("tables", []):
            try:
                table = create_mistral_table(table_data)
                mistral_tables.append(table)
            except Exception as e:
                logging.error(f"Error converting Mistral table: {e}")
        
        # Combine results
        result = {
            "page_number": page_number,
            "figures": figures,
            "tables": mistral_tables,
            "text_blocks": mistral_content.get("text_blocks", []),
            "raw_markdown": mistral_content.get("raw_markdown", ""),
            "processing_method": "hybrid"
        }
        
        logging.info(f"Hybrid processing complete: {len(figures)} figures, {len(mistral_tables)} tables")
        
        return result
    
    def process_pdf(self, pdf_path: str, total_pages: int) -> List[Dict[str, Any]]:
        """
        Process entire PDF using hybrid approach.
        
        Args:
            pdf_path: Path to PDF file
            total_pages: Total number of pages
            
        Returns:
            List of page results
        """
        results = []
        
        for page_num in range(1, total_pages + 1):
            try:
                # For now, we'll process each page individually
                # In a full implementation, you'd want to batch process
                mistral_content = self.mistral_ocr.process_pdf_page(pdf_path, page_num)
                
                # Convert to our format
                mistral_tables = []
                for table_data in mistral_content.get("tables", []):
                    try:
                        table = create_mistral_table(table_data)
                        mistral_tables.append(table)
                    except Exception as e:
                        logging.error(f"Error converting Mistral table on page {page_num}: {e}")
                
                results.append({
                    "page_number": page_num,
                    "figures": [],  # Will be filled by custom algorithm
                    "tables": mistral_tables,
                    "text_blocks": mistral_content.get("text_blocks", []),
                    "raw_markdown": mistral_content.get("raw_markdown", ""),
                    "processing_method": "hybrid"
                })
                
            except Exception as e:
                logging.error(f"Error processing page {page_num}: {e}")
                results.append({
                    "page_number": page_num,
                    "figures": [],
                    "tables": [],
                    "text_blocks": [],
                    "error": str(e),
                    "processing_method": "hybrid"
                })
        
        return results

def extract_tables_hybrid(img: np.ndarray, text_blocks: List, columns: List[Tuple[int, int]], 
                         page_width: int, pdf_path: str = None, page_number: int = 1) -> List[Table]:
    """
    Hybrid table extraction using Mistral OCR.
    
    Args:
        img: Page image
        text_blocks: Text blocks
        columns: Column boundaries
        page_width: Page width
        pdf_path: Path to PDF (for Mistral OCR)
        page_number: Page number
        
    Returns:
        List of detected tables
    """
    if not pdf_path:
        logging.warning("No PDF path provided, falling back to custom table detection")
        # Fallback to custom detection if no PDF path
        from .tables_ml import detect_tables_ml
        return detect_tables_ml(text_blocks, page_width, 1000)
    
    try:
        # Use Mistral OCR for table detection
        mistral_ocr = MistralOCR()
        mistral_content = mistral_ocr.process_pdf_page(pdf_path, page_number)
        
        # Convert Mistral tables to our format
        tables = []
        for table_data in mistral_content.get("tables", []):
            try:
                table = create_mistral_table(table_data)
                tables.append(table)
            except Exception as e:
                logging.error(f"Error converting Mistral table: {e}")
        
        return tables
        
    except Exception as e:
        logging.error(f"Error with Mistral OCR, falling back to custom detection: {e}")
        # Fallback to custom detection
        from .tables_ml import detect_tables_ml
        return detect_tables_ml(text_blocks, page_width, 1000)
