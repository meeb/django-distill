from django.core.exceptions import ImproperlyConfigured
from django.urls import URLPattern

distilled_urls = []
distilled_urls_by_name = {}


def add_distilled_url(pattern: URLPattern) -> None:
    """Register a URLPattern as a Distilled site pattern."""
    distilled_urls.append(pattern)
    distilled_urls_by_name.setdefault(pattern.distill_namespace, {})[pattern.name] = (
        pattern
    )


def get_distilled_urls() -> list[URLPattern]:
    """Return a list of all URLPattern objects which have been registered as a Distilled site pattern."""
    return distilled_urls


def get_distilled_url_by_name(
    name: str, namespace: str | dict | None = None
) -> URLPattern:
    """Return a URLPattern object which has been registered as a Distilled site pattern by name."""
    try:
        return distilled_urls_by_name[namespace][name]
    except KeyError:
        view_name = f"{namespace}:{name}" if namespace else name
        raise ImproperlyConfigured(
            f'The view "{view_name}" is not registered as a Distilled site path'
        )
