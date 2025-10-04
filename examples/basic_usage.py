#!/usr/bin/env python3
"""
Basic Usage Example for PDF Layout Analysis Engine

This example demonstrates how to use the PDF Layout Analysis Engine
to extract figures, tables, and text from PDF documents.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from runner import process_pdf
from pdf_io import get_page_info

def basic_example():
    """Basic example of processing a single PDF"""
    print("🔍 PDF Layout Analysis Engine - Basic Example")
    print("=" * 50)
    
    # Example PDF path (replace with your PDF)
    pdf_path = "sample_document.pdf"
    output_dir = "output"
    
    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        print("Please place a PDF file named 'sample_document.pdf' in the examples directory")
        return
    
    print(f"📄 Processing: {pdf_path}")
    print(f"📤 Output directory: {output_dir}")
    print()
    
    # Get PDF information
    try:
        pdf_info = get_page_info(pdf_path)
        print(f"📊 PDF Information:")
        print(f"   Pages: {pdf_info['num_pages']}")
        print(f"   Title: {pdf_info['metadata'].get('title', 'Unknown')}")
        print(f"   Author: {pdf_info['metadata'].get('author', 'Unknown')}")
        print()
    except Exception as e:
        print(f"⚠️  Warning: Could not get PDF info: {e}")
        print()
    
    # Process the PDF
    try:
        print("🚀 Starting processing...")
        result = process_pdf(pdf_path, output_dir)
        
        # Display results
        print("\n✅ Processing Complete!")
        print(f"📊 Results Summary:")
        print(f"   Pages processed: {len(result['pages'])}")
        
        total_figures = sum(len(p.get('figures', [])) for p in result['pages'])
        total_tables = sum(len(p.get('tables', [])) for p in result['pages'])
        
        print(f"   Figures detected: {total_figures}")
        print(f"   Tables detected: {total_tables}")
        
        # Show per-page breakdown
        print(f"\n📋 Per-page breakdown:")
        for i, page_data in enumerate(result['pages']):
            page_num = page_data['page_num'] + 1
            figures = len(page_data.get('figures', []))
            tables = len(page_data.get('tables', []))
            print(f"   Page {page_num}: {figures} figures, {tables} tables")
        
        print(f"\n📁 Output files saved to: {output_dir}/")
        print(f"📄 Summary report: {result['summary_path']}")
        
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        return

def debug_example():
    """Example of using debug mode to visualize layout analysis"""
    print("\n🔍 Debug Mode Example")
    print("=" * 30)
    
    # This would be used with the CLI
    print("To use debug mode, run:")
    print("python main.py --debug")
    print()
    print("This will generate overlay images showing:")
    print("🔴 Red: Column boundaries")
    print("🟢 Green: Text blocks")
    print("🔵 Blue: Detected figures")
    print("🟡 Yellow: Detected tables")

if __name__ == "__main__":
    basic_example()
    debug_example()
