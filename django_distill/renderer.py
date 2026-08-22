import errno
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from logging import getLogger
from types import TracebackType

from django.conf import settings
from django.urls import URLPattern
from django.utils.translation import activate as activate_lang
from typing_extensions import Self

from django_distill.urls import get_distilled_url_by_name, get_distilled_urls
from django_distill.utils import Path, get_header, get_langs

from .errors import DistillError, DistillRenderError
from .request import (
    generate_filename,
    generate_uri,
    get_static_filepath,
    get_uri_values,
    internal_wsgi_request,
)

log = getLogger("main")


def render_uri(
    uri: str, status_codes: tuple[int] | list[int]
) -> tuple[int, list[tuple[str, str]], bytes]:
    if not isinstance(status_codes, (tuple, list)):
        status_codes = (200,)
    status, headers, body = internal_wsgi_request(path=uri, method="GET")
    status_parts = status.split(" ", 1)
    try:
        status_code = int(status_parts[0])
    except ValueError:
        raise DistillRenderError(f"Invalid HTTP status: {status} for URI: {uri}")
    if status_code not in status_codes:
        raise DistillRenderError(f"Unexpected HTTP status: {status} for URI: {uri}")
    return status_code, headers, body


def render_pattern(
    pattern: URLPattern,
    param_set: list[str | None] | tuple[str | None] | tuple,
    language_code: str | None,
) -> tuple[str, str | None, int, list, bytes]:
    if language_code:
        activate_lang(language_code)
    generated_uri = generate_uri(pattern.distill_namespace, pattern.name, param_set)
    status, headers, body = render_uri(generated_uri, pattern.distill_status_codes)
    generated_filename = generate_filename(
        pattern.distill_file, generated_uri, param_set
    )
    return generated_uri, generated_filename, status, headers, body


def write_file(full_path: Path, content: bytes) -> None:
    try:
        if not full_path.parent.is_dir():
            log.info(f"Creating directory: {full_path.parent}")
            full_path.parent.mkdir(parents=True)
        with open(full_path, "wb") as f:
            f.write(content)
    except OSError as e:
        if e.errno == errno.EISDIR:
            raise DistillError(
                f'Output path "{full_path}" is a directory. '
                'Try adding a "distill_file" arg to your path(...)'
            )
        else:
            raise


def write_single_pattern(
    file_path: Path | str, pattern_name: str, *args: tuple | None, **kwargs: dict | None
) -> None:
    if isinstance(file_path, str):
        file_path = Path(file_path)
    pattern_name_parts = pattern_name.rsplit(":", 1)
    if len(pattern_name_parts) == 2:
        pattern_name = pattern_name_parts[1]
        namespace = pattern_name_parts[0]
    else:
        if "namespace" in kwargs:
            namespace = kwargs["namespace"]
            del kwargs["namespace"]
        else:
            namespace = None
    if "language_code" in kwargs:
        language_code = kwargs["language_code"]
        del kwargs["language_code"]
    else:
        language_code = None
    if args:
        param_set = args
    elif kwargs:
        param_set = kwargs
    else:
        param_set = ()
    pattern = get_distilled_url_by_name(pattern_name, namespace=namespace)
    generated_uri, generated_filename, _status, headers, body = render_pattern(
        pattern, param_set, language_code
    )
    mime = get_header(headers, "Content-Type")
    full_path, local_uri = get_static_filepath(
        file_path, generated_filename, generated_uri
    )
    log.info(
        f'Rendering single static page: {local_uri} -> {full_path} ("{mime}", {len(body)} bytes, from {pattern})'
    )
    write_file(Path(full_path), body)


def render_static_redirect(destination_url: str) -> bytes:
    redir = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="UTF-8">',
        f'<meta http-equiv="refresh" content="0;URL={destination_url}" />',
        f"<title>Redirecting to {destination_url}</title>",
        '<meta name="robots" content="noindex" />',
        "</head>",
        "<body>",
        f'<h1>Redirecting to <a href="{destination_url}">{destination_url}</a></h1>',
        f'<p>If you are not automatically redirected please click <a href="{destination_url}">this link</a></p>',
        "</html>",
    ]
    return "\n".join(redir).encode()


def render_redirects(output_dir: Path | str) -> bool:
    from django.contrib.redirects.models import Redirect

    if isinstance(output_dir, str):
        output_dir = Path(output_dir)
    for redirect in Redirect.objects.all():
        redirect_path = redirect.old_path.lstrip("/")
        if redirect_path.lower().endswith(".html"):
            redirect_file = redirect_path
        else:
            redirect_file = str(Path(redirect_path) / "index.html")
        full_path, local_uri = get_static_filepath(
            output_dir, redirect_file, redirect_file
        )
        content = render_static_redirect(redirect.new_path)
        log.info(
            f"Rendering redirect page: {local_uri} -> {full_path} (redirects to: {redirect_file})"
        )
        write_file(full_path, content)
    return True


class DistillRenderer:
    def __init__(
        self,
        urls_to_render: list[URLPattern] | None = None,
        hostname: str | None = None,
        enable_debug: bool = True,
        concurrency: int = 1,
    ) -> None:
        self._site_debug = settings.DEBUG
        self._site_allowed_hosts = settings.ALLOWED_HOSTS
        self._application = None
        if urls_to_render is None:
            self.urls_to_render = get_distilled_urls()
        else:
            self.urls_to_render = urls_to_render
        self.hostname = hostname
        self.enable_debug = enable_debug
        self.concurrency = concurrency

    def __enter__(self) -> Self:
        if self.hostname:
            settings.ALLOWED_HOSTS = [self.hostname]
        else:
            # Static sites generally want to ignore hostnames when being generated
            settings.ALLOWED_HOSTS = ["*"]
        if self.enable_debug:
            settings.DEBUG = True
        return self

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        # Restore any modified settings
        settings.ALLOWED_HOSTS = self._site_allowed_hosts
        settings.DEBUG = self._site_debug

    def get_urls_to_render(
        self,
    ) -> list[tuple[URLPattern, list[str | None] | tuple[str | None], str]]:
        to_render = []
        for url in self.urls_to_render:
            for param_set in get_uri_values(url.distill_func, url.name):
                if not param_set:
                    param_set = ()
                elif isinstance(param_set, str):
                    param_set = (param_set,)
                uri = generate_uri(url.distill_namespace, url.name, param_set)
                to_render.append((url, param_set, uri))
        return to_render

    def urls(self) -> Generator[str]:
        """Returns a list containing the generated URIs for all static site URL patterns. This does not render any
        HTML content, just returns the URLs for the static site URL patterns."""
        for url, param_set, uri in self.get_urls_to_render():
            yield uri

    def render(
        self,
    ) -> Generator[tuple[URLPattern, str, str, int, dict, bytes]]:
        """Iterates all static site URL patterns, then calls each URL generator function for each pattern.
        Yields the generated URI, filename, status, headers, and body."""

        def _render(item):
            rtn = []
            pattern, param_set, _uri = item
            for lang in get_langs():
                rtn.append((pattern,) + render_pattern(pattern, param_set, lang))
            return rtn

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            results = executor.map(_render, self.get_urls_to_render())
            for result in results:
                yield from result

    def render_to_directory(self, output_dir: Path | str) -> None:
        log.info(f"Rendering static site to directory: {output_dir}")
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)
        if not isinstance(output_dir, Path):
            raise DistillError(f"Invalid output directory: {output_dir}")
        for render in self.render():
            pattern, generated_uri, generated_filename, _status, headers, body = render
            mime = get_header(headers, "Content-Type")
            full_path, local_uri = get_static_filepath(
                output_dir, generated_filename, generated_uri
            )
            log.info(
                f'Rendering static page: {local_uri} -> {full_path} ("{mime}", {len(body)} bytes, from {pattern})'
            )
            write_file(Path(full_path), body)
        log.info("Rendering static site to directory complete")
