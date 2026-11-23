"""File signature checks for uploaded documents and media."""

import zipfile
from pathlib import Path


def upload_matches(path: Path, ext: str) -> bool:
    """Check binary formats before handing the file to a converter."""
    signatures = {
        "png": (b"\x89PNG\r\n\x1a\n",), "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",),
        "tif": (b"II*\0", b"MM\0*", b"II+\0", b"MM\0+"),
        "tiff": (b"II*\0", b"MM\0*", b"II+\0", b"MM\0+"),
        "ogg": (b"OggS",), "opus": (b"OggS",), "flac": (b"fLaC",),
        "webm": (b"\x1a\x45\xdf\xa3",), "mkv": (b"\x1a\x45\xdf\xa3",),
    }
    archive_member = {"docx": "word/document.xml", "xlsx": "xl/workbook.xml",
                      "epub": "META-INF/container.xml", "odt": "content.xml"}
    if ext in archive_member:
        try:
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                return (archive_member[ext] in archive.namelist() and len(entries) <= 20_000
                        and sum(entry.file_size for entry in entries) <= 512 * 1024 * 1024)
        except (OSError, zipfile.BadZipFile):
            return False
    with path.open("rb") as stream:
        head = stream.read(1024)
    if ext == "pdf":
        return b"%PDF-" in head
    if ext == "wav":
        return head.startswith((b"RIFF", b"RF64", b"RIFX")) and head[8:12] == b"WAVE"
    if ext in {"mp4", "m4a", "mov"}:
        return head[4:8] in {b"ftyp", b"moov", b"mdat", b"wide", b"free"}
    if ext in {"mp3", "aac"}:
        return head.startswith(b"ID3") or len(head) > 1 and head[0] == 255 and head[1] & 224 == 224
    return ext not in signatures or head.startswith(signatures[ext])
