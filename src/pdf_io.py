"""
PDF I/O operations - loading, rendering, coordinate conversion
"""
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from typing import Dict, List, Tuple, Optional, Any
import logging

# Constants - Reduced DPI for better performance
DPI_PAGE = 150  # Reduced from 600 for faster processing
DPI_CROP = 150  # Reduced from 600 for faster processing

def points_to_pixels(pt: float, dpi: int = DPI_PAGE) -> float:
    """Convert PDF points to pixels at given DPI"""
    return pt * (dpi / 72.0)

def pixels_to_points(px: float, dpi: int = DPI_PAGE) -> float:
    """Convert pixels to PDF points at given DPI"""
    return px * (72.0 / dpi)

def render_page(page: fitz.Page, dpi: int = DPI_PAGE) -> np.ndarray:
    """
    Render a PDF page to RGB image at specified DPI
    
    Args:
        page: PyMuPDF page object
        dpi: Target DPI for rendering
        
    Returns:
        RGB image as numpy array (H, W, 3)
    """
    # Get page dimensions in points
    rect = page.rect
    width_pt = rect.width
    height_pt = rect.height
    
    # Calculate pixel dimensions
    width_px = int(points_to_pixels(width_pt, dpi))
    height_px = int(points_to_pixels(height_pt, dpi))
    
    # Create transformation matrix for rendering
    mat = fitz.Matrix(dpi/72, dpi/72)
    
    # Render page to pixmap
    pix = page.get_pixmap(matrix=mat, alpha=False)
    
    # Convert to numpy array
    # Use PNG format and then convert to RGB
    img_data = pix.tobytes("png")
    from PIL import Image
    import io
    pil_img = Image.open(io.BytesIO(img_data))
    img = np.array(pil_img)
    
    # Ensure it's RGB
    if len(img.shape) == 3 and img.shape[2] == 3:
        pass  # Already RGB
    elif len(img.shape) == 2:
        # Convert grayscale to RGB
        img = np.stack([img, img, img], axis=2)
    else:
        # Convert to RGB
        img = img[:, :, :3]
    
    return img

def load_pdf_page_data(pdf_path: str, page_num: int) -> Dict[str, Any]:
    """
    Load comprehensive data from a PDF page
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        
    Returns:
        Dictionary containing all page data
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Get page dimensions
    rect = page.rect
    width_pt = rect.width
    height_pt = rect.height
    width_px = int(points_to_pixels(width_pt))
    height_px = int(points_to_pixels(height_pt))
    
    # Extract text data
    raw_dict = page.get_text("dict")
    words = page.get_text("words")
    
    # Extract drawings and images
    drawings = page.get_drawings()
    images = page.get_images(full=True)
    
    # Render page image
    img_page = render_page(page)
    
    # Heuristic for scanned page detection
    painted_image_area = 0.0
    if images:
        total_image_area = 0
        for img in images:
            # Get image rectangle in points
            img_rect = page.get_image_rects(img[0])[0]
            total_image_area += img_rect.width * img_rect.height
        painted_image_area = total_image_area / (width_pt * height_pt)
    
    is_scanned = (len(words) < 50) and (painted_image_area > 0.8)
    
    # Get image XObjects with their painted positions
    xobjects = []
    for img_index, img in enumerate(images):
        try:
            img_rects = page.get_image_rects(img[0])
            if img_rects:
                rect = img_rects[0]
                xobjects.append({
                    'index': img_index,
                    'bbox_pt': [rect.x0, rect.y0, rect.x1, rect.y1],
                    'bbox_px': [
                        int(points_to_pixels(rect.x0)),
                        int(points_to_pixels(rect.y0)),
                        int(points_to_pixels(rect.x1)),
                        int(points_to_pixels(rect.y1))
                    ],
                    'xref': img[0]
                })
        except Exception as e:
            logging.warning(f"Failed to get image rect for image {img_index}: {e}")
    
    doc.close()
    
    return {
        'page_size': {
            'pt': [width_pt, height_pt],
            'px': [width_px, height_px],
            'dpi': DPI_PAGE
        },
        'raw_dict': raw_dict,
        'words': words,
        'drawings': drawings,
        'images': images,
        'xobjects': xobjects,
        'img_page': img_page,
        'is_scanned': is_scanned,
        'painted_image_area': painted_image_area
    }

def crop_image_region(img: np.ndarray, bbox_px: List[int], dpi: int = DPI_CROP) -> np.ndarray:
    """
    Crop a region from the page image
    
    Args:
        img: Full page image
        bbox_px: Bounding box [x0, y0, x1, y1] in pixels
        dpi: DPI for the crop (usually same as page DPI)
        
    Returns:
        Cropped image region
    """
    x0, y0, x1, y1 = bbox_px
    # Ensure coordinates are within image bounds
    h, w = img.shape[:2]
    x0 = max(0, min(x0, w-1))
    y0 = max(0, min(y0, h-1))
    x1 = max(x0+1, min(x1, w))
    y1 = max(y0+1, min(y1, h))
    
    return img[y0:y1, x0:x1].copy()

def save_crop(img: np.ndarray, output_path: str) -> None:
    """Save cropped image to file"""
    # Ensure image is in the correct format for PIL
    if len(img.shape) == 3 and img.shape[2] == 3:
        # RGB image - ensure it's uint8
        if img.dtype != np.uint8:
            img = img.astype(np.uint8)
        pil_img = Image.fromarray(img, 'RGB')
    elif len(img.shape) == 2:
        # Grayscale image - ensure it's uint8
        if img.dtype != np.uint8:
            img = img.astype(np.uint8)
        pil_img = Image.fromarray(img, 'L')
    else:
        # Default to RGB
        if img.dtype != np.uint8:
            img = img.astype(np.uint8)
        pil_img = Image.fromarray(img, 'RGB')
    
    pil_img.save(output_path)

def get_page_info(pdf_path: str) -> Dict[str, Any]:
    """Get basic information about PDF"""
    doc = fitz.open(pdf_path)
    info = {
        'num_pages': len(doc),
        'metadata': doc.metadata,
        'page_sizes': []
    }
    
    for i in range(len(doc)):
        page = doc[i]
        rect = page.rect
        info['page_sizes'].append({
            'width_pt': rect.width,
            'height_pt': rect.height,
            'width_px': int(points_to_pixels(rect.width)),
            'height_px': int(points_to_pixels(rect.height))
        })
    
    doc.close()
    return info
