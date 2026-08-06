from collections.abc import Generator
from logging import getLogger
from pathlib import Path
from shutil import copy2

from django.conf import settings

log = getLogger("main")


def filter_static_dirs(dirs: list[str]) -> list[str]:
    skip_admin_dirs = bool(getattr(settings, "DISTILL_SKIP_ADMIN_DIRS", True))
    _ignore_dirs = []
    if skip_admin_dirs:
        _ignore_dirs = [
            "admin",
            "grappelli",
            "unfold",
        ]
    try:
        skip_dirs = list(getattr(settings, "DISTILL_SKIP_STATICFILES_DIRS", []))
    except (ValueError, TypeError):
        skip_dirs = []
    for d in skip_dirs:
        if isinstance(d, str):
            _ignore_dirs.append(d)
    return [d for d in dirs if d not in _ignore_dirs]


def copy_static(
    dir_from: Path | str, dir_to: Path | str
) -> Generator[tuple[Path, Path]]:
    if isinstance(dir_from, str):
        dir_from = Path(dir_from)
    if isinstance(dir_to, str):
        dir_to = Path(dir_to)
    for root, dirs, files in dir_from.walk():
        dirs[:] = filter_static_dirs(dirs)
        for f in files:
            from_path = root / f
            to_path = dir_to / from_path.relative_to(dir_from)
            to_path_dir = to_path.parent
            if not to_path_dir.is_dir():
                to_path_dir.mkdir(parents=True)
            copy2(from_path, to_path)
            yield from_path, to_path


def copy_static_and_media_files(
    output_dir: Path | str,
) -> bool:
    if isinstance(output_dir, str):
        output_dir = Path(output_dir)
    static_url = str(getattr(settings, "STATIC_URL", ""))
    static_root = str(getattr(settings, "STATIC_ROOT", ""))
    if static_url and static_root:
        static_root = Path(static_root)
        static_url = static_url.removeprefix("/")
        static_output_dir = output_dir / static_url
        for file_from, file_to in copy_static(static_root, static_output_dir):
            log.info(f"Copying static file: {file_from} -> {file_to}")
    else:
        log.error(
            "STATIC_URL and STATIC_ROOT must be set in settings.py to copy static files"
        )
    media_url = str(getattr(settings, "MEDIA_URL", ""))
    media_root = str(getattr(settings, "MEDIA_ROOT", ""))
    if media_url and media_root:
        media_root = Path(media_root)
        media_url = media_url.removeprefix("/")
        media_output_dir = output_dir / media_url
        for file_from, file_to in copy_static(media_root, media_output_dir):
            log.info(f"Copying media file: {file_from} -> {file_to}")
    else:
        log.warning(
            "MEDIA_URL and MEDIA_ROOT must be set in settings.py to copy media files"
        )
    return True
