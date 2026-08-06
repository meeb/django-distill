from django.http import HttpResponse
from django.urls import path


def test_url_in_no_namespace_view(request):
    return HttpResponse(b"test", content_type="application/octet-stream")


def test_no_param_func():
    return None


urlpatterns = [
    path(
        "sub-url-in-no-namespace",
        test_url_in_no_namespace_view,
        name="test_url_in_no_namespace",
        distill_path=True,
        distill_func=test_no_param_func,
    ),
]
