# ADR 0011: Download Orchestrator

## Status
Accepted

## Context
We have independent modules (URLParser, Downloaders, Storage) but no
central coordinator. The orchestrator will:
- Accept a URL
- Detect platform via URLParser
- Dispatch to the correct downloader
- Save results via StorageBackend
- Return a unified result

## Decision
Create `DownloadOrchestrator` service that:
1. Calls `URLParser.parse(url)` to detect platform
2. Instantiates the matched downloader
3. Calls `downloader.download(request)`
4. Calls `storage.save(media_info)`
5. Returns final result with file paths and metadata

## Implementation
```python
class DownloadOrchestrator:
    def __init__(self, storage: StorageBackend | None = None):
        self.storage = storage or LocalStorage()

    async def download(self, url: str, **kwargs) -> DownloadResult:
        parsed = URLParser.parse(url)
        downloader = parsed.downloader_class()
        request = DownloadRequest(url=url, **kwargs)
        media = await downloader.download(request)
        paths = self.storage.save(media)
        return DownloadResult(media=media, saved_paths=paths)
```

## Consequences
- Single entry point for all downloads
- Easy to add new platforms
- Simple Telegram bot integration
- No circular dependencies between modules
