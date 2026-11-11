"""Start the ADC simulator: python run.py   then open http://localhost:8000"""
import sys

from ui.server import serve

if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
