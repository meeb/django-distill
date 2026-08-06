from django_distill.urls import (
    add_distilled_url,
    get_distilled_url_by_name,
    get_distilled_urls,
)

__all__ = [
    "add_distilled_url",
    "get_distilled_url_by_name",
    "get_distilled_urls",
    "urls_to_distill",
]
__version__ = "4.0.1"


# Populated by django_distill.apps.DistillConfig.ready()
urls_to_distill = []
distill_path = None
distill_re_path = None
