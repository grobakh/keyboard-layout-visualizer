#!/usr/bin/env python3
from pathlib import Path
import sys

# Allow running the wrapper without installing the package first.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corne_layout_generator.cli import main


if __name__ == "__main__":
    main()
