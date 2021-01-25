from django.http import HttpResponse
from django_distill import distill_path
from django.urls import get_urlconf


app_name = 'test'


def test_url_in_deep_namespace_view(request):
    return HttpResponse(b'test', content_type='application/octet-stream')


def test_no_param_func():
    return None


urlpatterns = [

    distill_path('sub-url-in-sub-namespace',
        test_url_in_deep_namespace_view,
        name='test_url_in_namespace',
        distill_func=test_no_param_func,
        distill_file='test_url_in_sub_namespace'),

]
