"""Start Reel:  python run.py   then open http://127.0.0.1:8170"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from dotenv import load_dotenv  # optional
    load_dotenv()
except ImportError:
    pass

import uvicorn

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    port = int(os.getenv("REEL_PORT", "8170"))
    print(f"\n  Reel · turn any repo into a demo video  ->  http://127.0.0.1:{port}\n  API docs                                 ->  http://127.0.0.1:{port}/docs\n")
    uvicorn.run("reel.server:create_app", factory=True, host="127.0.0.1", port=port, log_level="warning")
