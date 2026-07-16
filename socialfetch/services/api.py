"""REST API server for SocialFetch using FastAPI."""

import logging
from pathlib import Path

from socialfetch.services.downloader import DownloadOrchestrator

logger = logging.getLogger(__name__)
orchestrator = DownloadOrchestrator()

_app: object = None  # cached FastAPI app


def _get_app():  # type: ignore[no-untyped-def]
    """Lazy init FastAPI to avoid import failure without api deps."""
    global _app
    if _app is not None:
        return _app
    from fastapi import FastAPI, HTTPException, Query  # noqa: F401
    from fastapi.responses import FileResponse  # noqa: F401

    app = FastAPI(title="SocialFetch API", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/download")
    async def api_download(
        url: str = Query(..., description="Social media URL to download"),
    ) -> dict[str, object]:
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
    async def serve_file(filename: str) -> FileResponse:
        path = Path("downloads") / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(path)

    _app = app
    return app


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    import uvicorn

    uvicorn.run(_get_app(), host=host, port=port, log_level="info")  # type: ignore[no-untyped-call]
