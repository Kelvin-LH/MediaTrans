"""Entry point: python run.py"""

import sys

from app.ui import run_app

if __name__ == "__main__":
    sys.exit(run_app(sys.argv))
