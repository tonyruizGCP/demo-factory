"""Module entrypoint for harness_optimizer.

Allows execution via `python -m harness_optimizer`.
"""
import sys
from pathlib import Path

try:
    from cli import main
except ImportError:
    # Ensure codebase root is on sys.path if invoked from outside directory
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from cli import main

if __name__ == "__main__":
    sys.exit(main())
