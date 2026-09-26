"""
Shruti Backend API Server.

The single server entrypoint for the Shruti FastAPI application.

Usage:
    # Run directly:
    python backend/src/server.py

    # Or from inside backend/src:
    python server.py

    # Or via Uvicorn:
    uvicorn server:app --reload --port 8000
"""

import sys
from pathlib import Path

# Ensure backend/src and root workspace are on Python module search path
_SRC_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _SRC_DIR.parent.parent

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(1, str(_WORKSPACE_ROOT))

from api.routes import create_app  # noqa: E402
from core.config import Settings  # noqa: E402

# Export standard ASGI application instance for Uvicorn / Gunicorn
settings = Settings()
app = create_app(settings)

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  Shruti Studio — API Server")
    print("=" * 60)
    print("  Server:   http://127.0.0.1:8000")
    print("  Swagger:  http://127.0.0.1:8000/api-docs")
    print("=" * 60)

    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(_SRC_DIR)],
    )
