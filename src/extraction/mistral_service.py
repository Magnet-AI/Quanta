"""
Mistral OCR integration for structured content extraction (tables, text).
We use this for everything except figures/images which use our custom algorithm.
"""

import os
import base64
import logging
import re
from typing import List, Dict, Any, Optional
from mistralai import Mistral
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MistralOCR:
    """Mistral OCR client for structured content extraction."""
    
    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY not found in environment variables")
        
        self.client = Mistral(api_key=self.api_key)
        self.model = "mistral-ocr-latest"
    
    def process_pdf_page(self, pdf_path: str, page_number: int) -> Dict[str, Any]:
        """
        Process a single PDF page using Mistral OCR.
        
        Args:
            pdf_path: Path to the PDF file
            page_number: Page number to process (1-indexed)
            
        Returns:
            Dictionary containing extracted content
        """
        try:
            print(f"    🔍 Processing PDF: {pdf_path}")
            print(f"    🔍 Page number: {page_number}")
            
            # Encode PDF to base64
            with open(pdf_path, "rb") as pdf_file:
                pdf_content = base64.b64encode(pdf_file.read()).decode('utf-8')
            
            print(f"    🔍 PDF encoded, size: {len(pdf_content)} characters")
            
            # Process with Mistral OCR
            print(f"    🔍 Calling Mistral OCR API...")
            response = self.client.ocr.process(
                model=self.model,
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{pdf_content}"
                },
                include_image_base64=True
            )
            
            print(f"    🔍 Mistral response type: {type(response)}")
            print(f"    🔍 Mistral response attributes: {dir(response)}")
            
            # Check what's actually in the response
            if hasattr(response, 'pages'):
                print(f"    🔍 Response has pages: {len(response.pages) if response.pages else 0}")
                if response.pages:
                    print(f"    🔍 First page keys: {list(response.pages[0].__dict__.keys()) if hasattr(response.pages[0], '__dict__') else 'No dict'}")
            
            # Extract tables and text from the response
            extracted_content = self._parse_ocr_response(response, page_number)
            
            return extracted_content
            
        except Exception as e:
            print(f"    ❌ Error processing PDF page {page_number} with Mistral OCR: {e}")
            import traceback
            traceback.print_exc()
            return {
                "page_number": page_number,
                "tables": [],
                "text_blocks": [],
                "error": str(e)
            }
    
    def _parse_ocr_response(self, response: Any, page_number: int) -> Dict[str, Any]:
        """
        Parse Mistral OCR response to extract tables and text.
        
        Args:
            response: Mistral OCR response
            page_number: Page number
            
        Returns:
            Parsed content dictionary
        """
        tables = []
        text_blocks = []
        markdown_content = ""
        
        try:
            # Extract markdown content from the specific page
            if hasattr(response, 'pages') and response.pages:
                # Get the specific page (page_number is 1-indexed, pages are 0-indexed)
                page_index = page_number - 1
                if 0 <= page_index < len(response.pages):
                    page = response.pages[page_index]
                    markdown_content = getattr(page, 'markdown', '')
                    print(f"    🔍 Page {page_number} markdown length: {len(markdown_content)}")
                    print(f"    🔍 Page {page_number} markdown preview: {markdown_content[:200]}...")
                else:
                    print(f"    ⚠️ Page {page_number} not found in response (has {len(response.pages)} pages)")
            else:
                print(f"    ⚠️ No pages found in response")
            
            # Parse tables from markdown
            tables = self._extract_tables_from_markdown(markdown_content)
            
            # Parse text blocks
            text_blocks = self._extract_text_blocks_from_markdown(markdown_content)
            
            print(f"    🔍 Parsed {len(tables)} tables, {len(text_blocks)} text blocks from markdown")
            
        except Exception as e:
            print(f"    ❌ Error parsing Mistral OCR response: {e}")
            import traceback
            traceback.print_exc()
        
        return {
            "page_number": page_number,
            "tables": tables,
            "text_blocks": text_blocks,
            "raw_markdown": markdown_content
        }
    
    def _extract_tables_from_markdown(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Extract tables from markdown content.
        
        Args:
            markdown: Markdown content from OCR
            
        Returns:
            List of table dictionaries
        """
        tables = []
        lines = markdown.split('\n')
        
        current_table = []
        in_table = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Check if line is a table row (contains |)
            if '|' in line:
                if not in_table:
                    in_table = True
                    current_table = []
                current_table.append(line)
            
            # Check if table ended
            elif in_table and (not line or not '|' in line):
                if current_table:
                    table_data = self._parse_table_rows(current_table)
                    if table_data:
                        tables.append({
                            "rows": table_data,
                            "bbox_px": [0, 0, 0, 0],  # Will be enhanced with bboxes if available
                            "detection_method": "mistral_ocr"
                        })
                        print(f"    🔍 Found table with {len(table_data)} rows")
                    current_table = []
                    in_table = False
        
        # Handle table at end of content
        if current_table:
            table_data = self._parse_table_rows(current_table)
            if table_data:
                tables.append({
                    "rows": table_data,
                    "bbox_px": [0, 0, 0, 0],
                    "detection_method": "mistral_ocr"
                })
                print(f"    🔍 Found final table with {len(table_data)} rows")
        
        return tables
    
    def _parse_table_rows(self, table_lines: List[str]) -> List[List[str]]:
        """
        Parse table rows from markdown lines.
        
        Args:
            table_lines: List of markdown table lines
            
        Returns:
            List of table rows (each row is a list of cells)
        """
        rows = []
        for line in table_lines:
            # Skip separator lines (lines with only |, -, and spaces)
            if re.match(r'^[\s\|\-]+$', line):
                continue
                
            # Split by | and clean up
            cells = [cell.strip() for cell in line.split('|')]
            # Remove empty cells at start/end
            if cells and not cells[0]:
                cells = cells[1:]
            if cells and not cells[-1]:
                cells = cells[:-1]
            
            # Only add rows that have meaningful content
            if cells and any(cell.strip() for cell in cells):
                rows.append(cells)
                print(f"    🔍 Table row: {cells}")
        
        return rows
    
    def _extract_text_blocks_from_markdown(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Extract text blocks from markdown content.
        
        Args:
            markdown: Markdown content from OCR
            
        Returns:
            List of text block dictionaries
        """
        text_blocks = []
        lines = markdown.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith('|') and not line.startswith('#'):
                text_blocks.append({
                    "text": line,
                    "bbox_px": [0, 0, 0, 0],  # Will be enhanced with bboxes if available
                    "line_number": i
                })
        
        return text_blocks
    
    def _enhance_tables_with_bboxes(self, tables: List[Dict], image_bboxes: List[Dict]) -> List[Dict]:
        """Enhance tables with bounding box information if available."""
        # This would require parsing the image_bboxes structure from Mistral
        # For now, return tables as-is
        return tables
    
    def _enhance_text_with_bboxes(self, text_blocks: List[Dict], image_bboxes: List[Dict]) -> List[Dict]:
        """Enhance text blocks with bounding box information if available."""
        # This would require parsing the image_bboxes structure from Mistral
        # For now, return text blocks as-is
        return text_blocks

def create_mistral_table(table_data: Dict[str, Any]) -> 'Table':
    """
    Convert Mistral table data to our Table class.
    
    Args:
        table_data: Table data from Mistral OCR
        
    Returns:
        Table object
    """
    from ..detection.table_detector import Table
    
    # Calculate bounding box (placeholder for now)
    bbox_px = table_data.get("bbox_px", [0, 0, 100, 100])
    
    # Convert rows to cells format
    cells = []
    for row in table_data.get("rows", []):
        row_cells = []
        for cell_text in row:
            row_cells.append({
                "text": cell_text,
                "bbox_px": [0, 0, 0, 0]  # Placeholder
            })
        cells.append(row_cells)
    
    return Table(
        bbox_px=bbox_px,
        cells=cells,
        detection_method="mistral_ocr"
    )
