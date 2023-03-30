from django.http import HttpResponse
from django_distill import distill_path


app_name = 'i18n'


def test_url_i18n_view(request):
    return HttpResponse(b'test', content_type='application/octet-stream')


def test_no_param_func():
    return None


urlpatterns = [

    distill_path('sub-url-with-i18n-prefix',
        test_url_i18n_view,
        name='test-url-i18n',
        distill_func=test_no_param_func,
        distill_file='test_url_i18n'),

]
