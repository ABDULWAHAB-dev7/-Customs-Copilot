"""Local server: the API plus the static page, on one port."""
from pathlib import Path

import uvicorn
from starlette.staticfiles import StaticFiles

from api.index import app

app.mount("/", StaticFiles(directory=str(Path(__file__).resolve().parent / "public"), html=True), name="public")

if __name__ == "__main__":
    uvicorn.run("dev:app", host="127.0.0.1", port=8000)
