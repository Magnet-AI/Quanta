#!/usr/bin/env python3
"""
Batch Processing Example for PDF Layout Analysis Engine

This example demonstrates how to process multiple PDFs in batch
and generate comprehensive reports.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from runner import process_pdf

def batch_process_pdfs(input_dir, output_dir):
    """
    Process all PDFs in a directory
    
    Args:
        input_dir (str): Directory containing PDF files
        output_dir (str): Output directory for results
    """
    print("🔄 PDF Layout Analysis Engine - Batch Processing")
    print("=" * 60)
    
    # Find all PDF files
    input_path = Path(input_dir)
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {input_dir}")
        return
    
    print(f"📁 Found {len(pdf_files)} PDF files to process")
    print(f"📤 Output directory: {output_dir}")
    print()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each PDF
    results = []
    total_figures = 0
    total_tables = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"📄 Processing {i}/{len(pdf_files)}: {pdf_file.name}")
        
        try:
            # Create individual output directory
            pdf_output_dir = os.path.join(output_dir, pdf_file.stem)
            
            # Process the PDF
            result = process_pdf(str(pdf_file), pdf_output_dir)
            
            # Count results
            pdf_figures = sum(len(p.get('figures', [])) for p in result['pages'])
            pdf_tables = sum(len(p.get('tables', [])) for p in result['pages'])
            
            total_figures += pdf_figures
            total_tables += pdf_tables
            
            # Store result summary
            results.append({
                'filename': pdf_file.name,
                'pages': len(result['pages']),
                'figures': pdf_figures,
                'tables': pdf_tables,
                'output_dir': pdf_output_dir,
                'status': 'success'
            })
            
            print(f"   ✅ Success: {pdf_figures} figures, {pdf_tables} tables")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                'filename': pdf_file.name,
                'pages': 0,
                'figures': 0,
                'tables': 0,
                'output_dir': None,
                'status': 'error',
                'error': str(e)
            })
        
        print()
    
    # Generate batch report
    generate_batch_report(results, output_dir, total_figures, total_tables)
    
    print("🎉 Batch processing complete!")
    print(f"📊 Total results: {total_figures} figures, {total_tables} tables")
    print(f"📄 Batch report: {os.path.join(output_dir, 'batch_report.json')}")

def generate_batch_report(results, output_dir, total_figures, total_tables):
    """Generate a comprehensive batch processing report"""
    
    # Calculate statistics
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    total_pages = sum(r['pages'] for r in successful)
    
    # Create report
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_files': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'total_pages': total_pages,
            'total_figures': total_figures,
            'total_tables': total_tables
        },
        'files': results,
        'statistics': {
            'avg_figures_per_page': total_figures / total_pages if total_pages > 0 else 0,
            'avg_tables_per_page': total_tables / total_pages if total_pages > 0 else 0,
            'success_rate': len(successful) / len(results) if results else 0
        }
    }
    
    # Save report
    report_path = os.path.join(output_dir, 'batch_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("📊 Batch Processing Summary:")
    print(f"   Files processed: {len(results)}")
    print(f"   Successful: {len(successful)}")
    print(f"   Failed: {len(failed)}")
    print(f"   Total pages: {total_pages}")
    print(f"   Total figures: {total_figures}")
    print(f"   Total tables: {total_tables}")
    print(f"   Success rate: {len(successful)/len(results)*100:.1f}%")
    
    if failed:
        print(f"\n❌ Failed files:")
        for result in failed:
            print(f"   - {result['filename']}: {result.get('error', 'Unknown error')}")

def main():
    """Main function"""
    # Example usage
    input_directory = "input_pdfs"  # Change this to your PDF directory
    output_directory = "batch_output"
    
    print("📁 Batch Processing Example")
    print("=" * 30)
    print(f"Input directory: {input_directory}")
    print(f"Output directory: {output_directory}")
    print()
    
    # Check if input directory exists
    if not os.path.exists(input_directory):
        print(f"❌ Input directory not found: {input_directory}")
        print("Please create the directory and add PDF files to process")
        return
    
    # Run batch processing
    batch_process_pdfs(input_directory, output_directory)

if __name__ == "__main__":
    main()
