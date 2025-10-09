import argparse
import sys
from pathlib import Path

from . import extract_document


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Quanta PDF extraction: figures, tables, and text"
    )
    parser.add_argument("--input", required=True, help="Path to input PDF file")
    parser.add_argument(
        "--output", required=True, help="Directory to write extracted artifacts"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug overlays in downstream tools"
    )

    args = parser.parse_args()
    input_pdf = Path(args.input)
    output_dir = Path(args.output)

    if not input_pdf.exists():
        print(f"❌ Input PDF not found: {input_pdf}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = extract_document(str(input_pdf), str(output_dir), debug=args.debug)
        pages = result.get("pages", [])
        total_figures = sum(len(p.get("figures", [])) for p in pages)
        total_tables = sum(len(p.get("tables", [])) for p in pages)
        print("✅ Extraction complete")
        print(f"Pages: {len(pages)} | Figures: {total_figures} | Tables: {total_tables}")
        summary_path = result.get("summary_path")
        if summary_path:
            print(f"Summary: {summary_path}")
        print(f"Artifacts written to: {output_dir}")
        return 0
    except Exception as exc:  # pragma: no cover
        print(f"❌ Extraction failed: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())


