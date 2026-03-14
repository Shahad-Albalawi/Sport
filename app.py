"""
Run the Sports Movement Analysis API server.

Canonical entry point: python main.py --serve
This file exists for backward compatibility; prefer: python main.py --serve
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend.api.server import run_server

if __name__ == "__main__":
    run_server()
