from django.conf import settings
from django.http import HttpResponse
from django_distill import distill_url, distill_path, distill_re_path


def test_no_param_view(request):
    return HttpResponse(b'test',
                        content_type='application/octet-stream')


def test_positional_param_view(request, param):
    return HttpResponse(b'test' + param.encode(),
                        content_type='application/octet-stream')


def test_named_param_view(request, param=None):
    return HttpResponse(b'test' + param.encode(),
                        content_type='application/octet-stream')


def test_broken_view(request):
    # Trigger a normal Python exception when rendering
    a = 1 / 0


def test_no_param_func():
    return None


def test_positional_param_func():
    return ('12345',)


def test_named_param_func():
    return [{'param': 'test'}]


urlpatterns = [

    distill_url(r'^url/$',
                test_no_param_view,
                name='url-no-param',
                distill_func=test_no_param_func,
                distill_file='test'),
    distill_url(r'^url/([\d]+)$',
                test_positional_param_view,
                name='url-positional-param',
                distill_func=test_positional_param_func),
    distill_url(r'^url/(?P<param>[\w]+)$',
                test_named_param_view,
                name='url-named-param',
                distill_func=test_named_param_func),
]


if settings.HAS_RE_PATH:
    urlpatterns += [

        distill_re_path(r'^re_path/$',
                        test_no_param_view,
                        name='re_path-no-param',
                        distill_func=test_no_param_func,
                        distill_file='test'),
        distill_re_path(r'^re_path/([\d]+)$',
                        test_positional_param_view,
                        name='re_path-positional-param',
                        distill_func=test_positional_param_func),
        distill_re_path(r'^re_path/(?P<param>[\w]+)$',
                        test_named_param_view,
                        name='re_path-named-param',
                        distill_func=test_named_param_func),
        distill_re_path(r'^re_path/broken$',
                        test_broken_view,
                        name='re_path-broken',
                        distill_func=test_no_param_func),

    ]


if settings.HAS_PATH:
    urlpatterns += [

        distill_path('path/',
                    test_no_param_view,
                    name='path-no-param',
                    distill_func=test_no_param_func,
                    distill_file='test'),
        distill_path('path/<int>',
                    test_positional_param_view,
                    name='path-positional-param',
                    distill_func=test_positional_param_func),
        distill_path('path/<str:param>',
                    test_named_param_view,
                    name='path-named-param',
                    distill_func=test_named_param_func),
        distill_path('path/broken',
                    test_broken_view,
                    name='path-broken',
                    distill_func=test_no_param_func),

    ]
