"""
Extract annotations from visually annotated PDFs (hand-drawn annotations)
"""
import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

class VisualAnnotationExtractor:
    def __init__(self):
        # Color ranges for different annotation types
        self.color_ranges = {
            'red': {
                'lower': np.array([0, 50, 50]),
                'upper': np.array([10, 255, 255])
            },
            'green': {
                'lower': np.array([40, 50, 50]),
                'upper': np.array([80, 255, 255])
            },
            'blue': {
                'lower': np.array([100, 50, 50]),
                'upper': np.array([130, 255, 255])
            }
        }
        
        self.label_mapping = {
            'red': 'table',
            'green': 'figure',
            'blue': 'text'
        }
    
    def extract_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract hand-drawn annotations from PDF by analyzing the visual content
        
        Args:
            pdf_path: Path to annotated PDF
            
        Returns:
            List of detected annotations
        """
        doc = fitz.open(pdf_path)
        all_annotations = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Render page to image
            mat = fitz.Matrix(2, 2)  # Higher resolution for better detection
            pix = page.get_pixmap(matrix=mat)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            
            if img.shape[2] == 4:  # RGBA
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
            elif img.shape[2] == 1:  # Grayscale
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            
            # Detect colored annotations
            page_annotations = self._detect_colored_boxes(img, page_num, pdf_path)
            all_annotations.extend(page_annotations)
        
        doc.close()
        return all_annotations
    
    def _detect_colored_boxes(self, img: np.ndarray, page_num: int, pdf_path: str) -> List[Dict[str, Any]]:
        """Detect colored boxes in the image"""
        annotations = []
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        
        for color_name, color_range in self.color_ranges.items():
            # Create mask for this color
            mask = cv2.inRange(hsv, color_range['lower'], color_range['upper'])
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Filter out very small contours
                area = cv2.contourArea(contour)
                if area < 1000:  # Minimum area threshold
                    continue
                
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Convert back to original PDF coordinates (150 DPI)
                scale_factor = 150 / (2 * 72)  # 2x scale factor from rendering
                x0 = int(x / scale_factor)
                y0 = int(y / scale_factor)
                x1 = int((x + w) / scale_factor)
                y1 = int((y + h) / scale_factor)
                
                # Create annotation data
                annotation = {
                    'pdf_path': pdf_path,
                    'page_num': page_num,
                    'bbox_px': [x0, y0, x1, y1],
                    'label': self.label_mapping[color_name],
                    'color': color_name,
                    'area': (x1 - x0) * (y1 - y0),
                    'width': x1 - x0,
                    'height': y1 - y0,
                    'center_x': (x0 + x1) / 2,
                    'center_y': (y0 + y1) / 2,
                    'confidence': min(1.0, area / 10000)  # Confidence based on size
                }
                
                annotations.append(annotation)
        
        return annotations
    
    def extract_all_pdfs(self, annotated_pdfs_dir: str) -> List[Dict[str, Any]]:
        """Extract annotations from all PDFs in directory"""
        pdf_dir = Path(annotated_pdfs_dir)
        all_annotations = []
        
        for pdf_file in pdf_dir.glob("*.pdf"):
            if pdf_file.name == ".DS_Store":
                continue
                
            logging.info(f"Extracting visual annotations from {pdf_file.name}")
            annotations = self.extract_from_pdf(str(pdf_file))
            all_annotations.extend(annotations)
            
            logging.info(f"Found {len(annotations)} visual annotations in {pdf_file.name}")
        
        return all_annotations

def main():
    """Test the visual annotation extractor"""
    extractor = VisualAnnotationExtractor()
    
    # Extract from your annotated PDFs
    annotations = extractor.extract_all_pdfs("../dataset/annotated_pdfs")
    
    # Save to file
    import json
    output_file = "data/raw/visual_annotations.json"
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(annotations, f, indent=2)
    
    print(f"Extracted {len(annotations)} visual annotations")
    print(f"Saved to {output_file}")
    
    # Show summary
    label_counts = {}
    for ann in annotations:
        label = ann['label']
        label_counts[label] = label_counts.get(label, 0) + 1
    
    print("\nVisual annotation summary:")
    for label, count in label_counts.items():
        print(f"  {label}: {count}")

if __name__ == "__main__":
    main()
