from __future__ import annotations

import os
from pathlib import Path

import uvicorn

SERVER_DIR=Path(__file__).resolve().parent

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        app_dir=str(SERVER_DIR),
        host="0.0.0.0",
        port=int(os.getenv("PORT","4000")),
        reload=True,
    )
