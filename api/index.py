import os
import sys

# Add project root to sys.path so app modules are resolved seamlessly on Vercel
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.main import app

# Vercel serverless entrypoint
handler = app
