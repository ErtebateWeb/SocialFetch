"""REST API server for SocialFetch using FastAPI."""
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from socialfetch.services.downloader import DownloadOrchestrator

logger = logging.getLogger(__name__)

app = FastAPI(title="SocialFetch API", version="0.1.0")
orchestrator = DownloadOrchestrator()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/download")
async def api_download(
    url: str = Query(..., description="Social media URL to download"),
):
    """Download media from a social media URL.

    Returns JSON with media info + file(s) as temporary links.
    """
    result = await orchestrator.download(url)

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    if not result.saved_paths:
        raise HTTPException(status_code=400, detail="No files downloaded")

    return {
        "url": result.url,
        "platform": result.platform,
        "media": {
            "type": result.media.media_type.name,
            "caption": result.media.caption,
            "author": result.media.author,
        },
        "files": [
            {
                "path": p,
                "filename": Path(p).name,
                "size": Path(p).stat().st_size,
            }
            for p in result.saved_paths
        ],
    }


@app.get("/file/{filename:path}")
async def serve_file(filename: str):
    """Serve a downloaded file by filename."""
    path = Path("downloads") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    uvicorn.run(app, host=host, port=port, log_level="info")
