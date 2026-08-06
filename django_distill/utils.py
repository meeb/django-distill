import os
import tempfile
from binascii import hexlify
from collections.abc import Generator
from pathlib import Path

from django.conf import global_settings, settings
from django.urls import URLPattern, URLResolver, get_resolver


def set_func_attr(name, value):
    """Decorator for setting an arbitrary function attribute. Only used for tests to mark certain views."""

    def decorator(func):
        setattr(func, name, value)
        return func

    return decorator


def iter_url_patterns(
    url_patterns: list | None = None, namespace: str | None = "", depth: int = 0
) -> Generator[tuple[URLPattern, str | None, int]]:
    """
    Yield tuples of (URLPattern, namespace) for all URLPattern objects in the
    provided Django URLconf, or the default one if none is provided.
    """
    if url_patterns is None:
        url_patterns = get_resolver().url_patterns
    for pattern in url_patterns:
        if isinstance(pattern, URLPattern):
            if depth == 0:
                namespace = None
            yield pattern, namespace, 1
        elif isinstance(pattern, URLResolver):
            if pattern.namespace:
                if namespace:
                    namespace = f"{namespace}:{pattern.namespace}"
                else:
                    namespace = pattern.namespace
            else:
                namespace = None
            yield from iter_url_patterns(pattern.url_patterns, namespace, depth + 1)
        else:
            if namespace is None:
                namespace = ""
            raise TypeError(f"Unexpected pattern type: {type(pattern)} in {namespace}")


def get_header(headers: list[tuple[str, str]], name: str) -> str | None:
    """Returns the value of a header by name from a list of headers. If multiple headers with the same name exist,
    then return the first one."""
    lower_name = name.lower()
    for header_name, header_value in headers:
        if header_name.lower() == lower_name:
            return header_value
    return None


def get_langs() -> list[str]:
    """Returns a list of language codes for all languages configured in the project."""
    langs = []
    language_code = str(getattr(settings, "LANGUAGE_CODE", "en"))
    global_languages = list(getattr(global_settings, "LANGUAGES", []))
    try:
        languages = list(getattr(settings, "LANGUAGES", []))
    except (ValueError, TypeError, AttributeError):
        languages = []
    try:
        distill_languages = list(getattr(settings, "DISTILL_LANGUAGES", []))
    except (ValueError, TypeError, AttributeError):
        distill_languages = []
    if languages != global_languages:
        for lang_code, lang_name in languages:
            langs.append(lang_code)
    if language_code not in distill_languages and language_code not in langs:
        langs.append(language_code)
    for lang in distill_languages:
        langs.append(str(lang))
    return sorted(langs)


class NamedTestFile:
    """
    A class that mimics tempfile.NamedTemporaryFile but is pre-populated with
    random contents and closed. It also mimics some Path methods for
    backwards compatibility.
    """

    def __init__(self):
        self._temp_file = tempfile.NamedTemporaryFile(delete=False)  # noqa: SIM115
        self._temp_file.write(hexlify(os.urandom(16)))
        self._temp_file.close()
        self.name = self._temp_file.name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unlink()

    def __fspath__(self):
        return self.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"NamedTestFile('{self.name}')"

    @property
    def path(self) -> Path:
        return Path(self.name)

    def unlink(self):
        if os.path.exists(self.name):
            os.unlink(self.name)
