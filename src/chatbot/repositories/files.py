import mimetypes
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from chatbot.config import settings


MAX_FILE_SIZE = 10 * 1024 * 1024


def workspace(user_id: str | uuid.UUID, conversation_id: str | uuid.UUID) -> Path:
    path = Path(settings.tool_workspace).resolve() / str(user_id) / str(conversation_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_path(root: Path, path: str) -> Path:
    if not path or Path(path).is_absolute():
        raise ValueError("Use a non-empty relative path")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Path must stay inside the conversation workspace")
    return resolved


def describe(path: Path, root: Path) -> dict:
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    relative = path.relative_to(root)
    return {
        "name": relative.as_posix(),
        "size": path.stat().st_size,
        "content_type": media_type,
        "source": "uploaded" if relative.parts[0] == "uploaded" else "generated",
    }


def list_files(root: Path) -> list[dict]:
    return [describe(path, root) for path in sorted(root.rglob("*")) if path.is_file()]


async def save_upload(root: Path, upload: UploadFile) -> dict:
    name = upload.filename or ""
    if not name or Path(name).name != name or "\\" in name:
        raise ValueError("Invalid filename")
    destination = safe_path(root, f"uploaded/{name}")
    destination.parent.mkdir(exist_ok=True)
    created = False
    try:
        with destination.open("xb") as output:
            created = True
            size = 0
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise ValueError("File exceeds the 10 MB limit")
                output.write(chunk)
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
    return describe(destination, root)


def delete_workspace(root: Path) -> None:
    shutil.rmtree(root, ignore_errors=True)
