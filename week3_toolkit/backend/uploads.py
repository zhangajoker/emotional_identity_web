import os
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
MAX_VIDEO_SECONDS = 60
MAX_ANALYZED_VIDEO_FRAMES = 120

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
}

ALLOWED_VIDEO_SUFFIXES = {
    ".mp4",
    ".mov",
    ".webm",
}


async def read_upload_limited(
    file: UploadFile,
    max_bytes: int,
) -> bytes:
    chunks: list[bytes] = []
    total_size = 0

    while True:
        chunk = await file.read(1024 * 1024)

        if not chunk:
            break

        total_size += len(chunk)

        if total_size > max_bytes:
            limit_mb = max_bytes // (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"文件不能超过 {limit_mb}MB",
            )

        chunks.append(chunk)

    return b"".join(chunks)


async def save_video_upload_limited(
    file: UploadFile,
    max_bytes: int,
) -> str:
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in ALLOWED_VIDEO_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail="仅支持 MP4、MOV 或 WebM 视频",
        )

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )
    temp_path = temp_file.name
    total_size = 0

    try:
        while True:
            chunk = await file.read(1024 * 1024)

            if not chunk:
                break

            total_size += len(chunk)

            if total_size > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="视频不能超过 50MB",
                )

            temp_file.write(chunk)
    except Exception:
        temp_file.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    else:
        temp_file.close()
        return temp_path