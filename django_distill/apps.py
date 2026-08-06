from functools import partial
from types import FunctionType

from django import urls
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.urls import URLPattern, URLResolver, conf, resolvers
from django.urls.resolvers import RegexPattern, RoutePattern

import django_distill
from django_distill.urls import add_distilled_url, get_distilled_urls
from django_distill.utils import iter_url_patterns


def null_generator():
    pass


def _distilled_path(
    route: str,
    view: FunctionType,
    kwargs: dict | None = None,
    name: str | None = None,
    distill_path: bool = False,
    distill_func: FunctionType | None = None,
    distill_file: str | None = None,
    distill_status_codes: tuple[int] | None = None,
    Pattern: RegexPattern | RoutePattern | None = None,
) -> URLResolver | URLPattern:
    pattern_or_resolver = conf._path(route, view, kwargs, name, Pattern=Pattern)
    if distill_path and isinstance(pattern_or_resolver, resolvers.URLPattern):
        if distill_func is None:
            distill_func = null_generator
        if distill_status_codes is None:
            distill_status_codes = (200,)
        if not callable(distill_func):
            raise ImproperlyConfigured(
                'When registering a distilled site path the URLs generator argument "distill_func" must be None or a callable'
            )
        if name is None:
            raise ImproperlyConfigured(
                'When registering a distilled site path the "name" argument must be provided'
            )
        if distill_file is not None and not isinstance(distill_file, str):
            raise ImproperlyConfigured(
                'When registering a distilled site path the "distill_file" argument must None or a string'
            )
        if not all(
            isinstance(status_code, int) for status_code in distill_status_codes
        ):
            raise ImproperlyConfigured(
                'When registering a distilled site path the "distill_status_codes" argument must None or an iterable of integers'
            )
        # resolvers.URLPattern needs some additional attributes to store the Distill details
        pattern_or_resolver.is_distilled = True
        pattern_or_resolver.distill_namespace = None
        pattern_or_resolver.distill_func = distill_func
        pattern_or_resolver.distill_file = distill_file
        pattern_or_resolver.distill_status_codes = distill_status_codes
    return pattern_or_resolver


def _distilled_path_enabled(*args, **kwargs) -> URLResolver | URLPattern:
    """
    Wrapper for _distilled_path called by the legacy distill_path function which defaults distill_path to True.
    """
    kwargs["distill_path"] = True
    return _distilled_path(*args, **kwargs)


class DistillConfig(AppConfig):
    name = "django_distill"

    def ready(self) -> None:
        """
        Monkeypatch path and re_path. Currently, this patches _path.
        This also adds new attributes to the URLPattern objects to store the required data for static site generation.
        """
        urls.conf.path = partial(_distilled_path, Pattern=RoutePattern)
        urls.conf.re_path = partial(_distilled_path, Pattern=RegexPattern)
        urls.path = urls.conf.path
        urls.re_path = urls.conf.re_path

        # Shims to make the interface compatible with django_distill > 4.0.0
        django_distill.distill_path = partial(
            _distilled_path_enabled, Pattern=RoutePattern
        )
        django_distill.distill_re_path = partial(
            _distilled_path_enabled, Pattern=RegexPattern
        )

        # Iterate all loaded URLs and store any URLs defined as a Distilled path.
        for pattern, namespace, _ in iter_url_patterns():
            if getattr(pattern, "is_distilled", False):
                # Make sure the Distilled path knows its namespace
                pattern.distill_namespace = namespace
                add_distilled_url(pattern)

        # Shims to make the interface compatible with django_distill > 4.0.0
        django_distill.urls_to_distill = get_distilled_urls()
