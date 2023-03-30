from django.http import HttpResponse
from django_distill import distill_path


app_name = 'no-namespaced-urls'


def test_url_in_no_namespace_view(request):
    return HttpResponse(b'test', content_type='application/octet-stream')


def test_no_param_func():
    return None


urlpatterns = [

    distill_path('sub-url-in-no-namespace',
        test_url_in_no_namespace_view,
        name='test_url_in_no_namespace',
        distill_func=test_no_param_func,
        distill_file='test_url_in_no_namespace'),

]
