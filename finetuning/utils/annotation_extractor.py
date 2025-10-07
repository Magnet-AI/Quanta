"""
Extract annotations from annotated PDFs
"""
import fitz  # PyMuPDF
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

class AnnotationExtractor:
    def __init__(self):
        self.color_mapping = {
            (1.0, 0.0, 0.0): 'table',      # Red
            (0.0, 1.0, 0.0): 'figure',     # Green  
            (0.0, 0.0, 1.0): 'text',       # Blue
            (1.0, 1.0, 0.0): 'caption',    # Yellow
            (1.0, 0.0, 1.0): 'header',     # Purple
        }
    
    def extract_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract annotations from a single PDF
        
        Args:
            pdf_path: Path to annotated PDF
            
        Returns:
            List of annotation data
        """
        doc = fitz.open(pdf_path)
        annotations = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get page dimensions
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Get all annotations on this page
            page_annotations = page.annots()
            
            for annot in page_annotations:
                if annot.type[0] == fitz.PDF_ANNOT_RECT:  # Rectangle annotation
                    annotation_data = self._extract_annotation_data(
                        annot, page_num, page_width, page_height, pdf_path
                    )
                    if annotation_data:
                        annotations.append(annotation_data)
        
        doc.close()
        return annotations
    
    def _extract_annotation_data(self, annot, page_num: int, page_width: float, 
                                page_height: float, pdf_path: str) -> Dict[str, Any]:
        """Extract data from a single annotation"""
        try:
            # Get annotation rectangle
            rect = annot.rect
            
            # Convert to pixels (assuming 150 DPI)
            dpi = 150
            x0 = int(rect.x0 * (dpi / 72))
            y0 = int(rect.y0 * (dpi / 72))
            x1 = int(rect.x1 * (dpi / 72))
            y1 = int(rect.y1 * (dpi / 72))
            
            # Get annotation color
            color = annot.colors.get('stroke', (0, 0, 0))
            if isinstance(color, tuple) and len(color) == 3:
                # Normalize color values
                color = tuple(c / 255.0 for c in color)
            else:
                color = (0, 0, 0)  # Default to black
            
            # Map color to label
            label = self._get_label_from_color(color)
            
            if label:
                return {
                    'pdf_path': pdf_path,
                    'page_num': page_num,
                    'bbox_px': [x0, y0, x1, y1],
                    'bbox_points': [rect.x0, rect.y0, rect.x1, rect.y1],
                    'label': label,
                    'color': color,
                    'area': (x1 - x0) * (y1 - y0),
                    'width': x1 - x0,
                    'height': y1 - y0,
                    'center_x': (x0 + x1) / 2,
                    'center_y': (y0 + y1) / 2,
                }
        except Exception as e:
            logging.warning(f"Error extracting annotation: {e}")
            return None
        
        return None
    
    def _get_label_from_color(self, color: Tuple[float, float, float]) -> str:
        """Get label from color with tolerance for slight variations"""
        # Find closest color match
        min_distance = float('inf')
        best_label = None
        
        for ref_color, label in self.color_mapping.items():
            distance = sum((a - b) ** 2 for a, b in zip(color, ref_color))
            if distance < min_distance:
                min_distance = distance
                best_label = label
        
        # Only return label if color is close enough
        if min_distance < 0.1:  # Tolerance for color variations
            return best_label
        
        return None
    
    def extract_all_pdfs(self, annotated_pdfs_dir: str) -> List[Dict[str, Any]]:
        """
        Extract annotations from all PDFs in directory
        
        Args:
            annotated_pdfs_dir: Directory containing annotated PDFs
            
        Returns:
            List of all annotation data
        """
        pdf_dir = Path(annotated_pdfs_dir)
        all_annotations = []
        
        for pdf_file in pdf_dir.glob("*.pdf"):
            if pdf_file.name == ".DS_Store":
                continue
                
            logging.info(f"Extracting annotations from {pdf_file.name}")
            annotations = self.extract_from_pdf(str(pdf_file))
            all_annotations.extend(annotations)
            
            logging.info(f"Found {len(annotations)} annotations in {pdf_file.name}")
        
        return all_annotations

def main():
    """Test the annotation extractor"""
    extractor = AnnotationExtractor()
    
    # Extract from your annotated PDFs
    annotations = extractor.extract_all_pdfs("../dataset/annotated_pdfs")
    
    # Save to file
    output_file = "data/raw/extracted_annotations.json"
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(annotations, f, indent=2)
    
    print(f"Extracted {len(annotations)} annotations")
    print(f"Saved to {output_file}")
    
    # Show summary
    label_counts = {}
    for ann in annotations:
        label = ann['label']
        label_counts[label] = label_counts.get(label, 0) + 1
    
    print("\nAnnotation summary:")
    for label, count in label_counts.items():
        print(f"  {label}: {count}")

if __name__ == "__main__":
    main()
