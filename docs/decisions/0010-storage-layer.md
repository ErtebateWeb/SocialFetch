# ADR 0010: Storage Layer

## Status
Accepted

## Context
Downloaded media needs a consistent, organized storage system.
Requirements:
- Platform-based directory structure
- Metadata persistence (JSON sidecar files)
- Future support for cloud storage (S3, etc.)
- Clean temp file management

## Decision
### Interface
Abstract `StorageBackend` with two implementations:
- `LocalStorage` — filesystem storage (primary)
- (Future) `S3Storage`, `GCSStorage`

### Directory Layout
```
downloads/
├── instagram/
│   ├── ABC123/
│   │   ├── image_1.jpg
│   │   ├── image_2.jpg
│   │   └── .meta.json          ← sidecar metadata
│   └── DEF456/
│       └── video.mp4
│       └── .meta.json
├── youtube/
└── tiktok/
```

### Metadata
Each download produces a JSON sidecar file (`.meta.json`) with:
- Original URL
- Download timestamp
- File list with sizes
- Caption, author, platform metadata

## Consequences
- Consistent organization across platforms
- Machine-readable metadata for future API
- Easy to add cloud backends later
- Slightly more I/O for metadata writes
