#!/bin/bash
# Script to upload quanta-pdf to PyPI
# Usage: ./upload_to_pypi.sh

cd "$(dirname "$0")"
source .venv/bin/activate

# Check if credentials are set
if [ -z "$TWINE_USERNAME" ] || [ -z "$TWINE_PASSWORD" ]; then
    echo "Please set TWINE_USERNAME and TWINE_PASSWORD environment variables"
    echo "Example:"
    echo "  export TWINE_USERNAME=__token__"
    echo "  export TWINE_PASSWORD=pypi-xxxxxxxxxxxxx"
    echo ""
    echo "Or run manually:"
    echo "  source .venv/bin/activate"
    echo "  python -m twine upload dist/*"
    exit 1
fi

python -m twine upload dist/*


