from django.http import HttpResponse
from django.urls import include, path

app_name = "namespaced-urls"


def test_url_in_namespace_view(request):
    return HttpResponse(b"test", content_type="application/octet-stream")


def test_no_param_func():
    return None


urlpatterns = [
    path(
        "sub-url-in-namespace",
        test_url_in_namespace_view,
        name="test_url_in_namespace",
        distill_path=True,
        distill_func=test_no_param_func,
    ),
    path(
        "path/sub-namespace/",
        include("tests.namespaced_sub_urls", namespace="sub_test_namespace"),
    ),
    # Uncomment to trigger a DistillError for including the same sub-urls more than
    # once in a single project which is unsupported
    # path('path/sub-namespace1/',
    #    include('tests.namespaced_sub_urls', namespace='sub_test_namespace1')),
]
