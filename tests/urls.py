from django.conf import settings
from django.http import HttpResponse
from django.urls import include, path
from django.contrib.flatpages.views import flatpage as flatpage_view
from django.apps import apps as django_apps
from django_distill import distill_url, distill_path, distill_re_path


def test_no_param_view(request):
    return HttpResponse(b'test', content_type='application/octet-stream')


def test_positional_param_view(request, param):
    return HttpResponse(b'test' + param.encode(),
                        content_type='application/octet-stream')


def test_named_param_view(request, param=None):
    return HttpResponse(b'test' + param.encode(),
                        content_type='application/octet-stream')


def test_session_view(request):
    request.session['test'] = 'test'
    return HttpResponse(b'test', content_type='application/octet-stream')


def test_broken_view(request):
    # Trigger a normal Python exception when rendering
    a = 1 / 0


def test_http404_view(request):
    response = HttpResponse(b'404', content_type='application/octet-stream')
    response.status_code = 404
    return response


def test_no_param_func():
    return None


def test_positional_param_func():
    return ('12345',)


def test_named_param_func():
    return [{'param': 'test'}]


def test_flatpages_func():
    Site = django_apps.get_model('sites.Site')
    current_site = Site.objects.get_current()
    flatpages = current_site.flatpage_set.filter(registration_required=False)
    for flatpage in flatpages:
        yield {'url': flatpage.url}


urlpatterns = [

    distill_url(r'^url/$',
        test_no_param_view,
        name='url-no-param',
        distill_func=test_no_param_func,
        distill_file='test'),
    distill_url(r'^url-no-func/$',
        test_no_param_view,
        name='url-no-param-no-func',
        distill_file='test'),
    distill_url(r'^url/([\d]+)$',
        test_positional_param_view,
        name='url-positional-param',
        distill_func=test_positional_param_func),
    distill_url(r'^url/(?P<param>[\w]+)$',
        test_named_param_view,
        name='url-named-param',
        distill_func=test_named_param_func),
    path('path/namespace1/',
        include('tests.namespaced_urls', namespace='test_namespace')),
    path('path/no-namespace/',
        include('tests.no_namespaced_urls')),

]


if settings.HAS_RE_PATH:
    urlpatterns += [

        distill_re_path(r'^re_path/$',
            test_no_param_view,
            name='re_path-no-param',
            distill_func=test_no_param_func,
            distill_file='test'),
        distill_re_path(r'^re_path-no-func/$',
            test_no_param_view,
            name='re_path-no-param-no-func',
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
        distill_re_path(r'^re_path/ignore-sessions$',
            test_session_view,
            name='re_path-ignore-sessions',
            distill_func=test_no_param_func),
        distill_re_path(r'^re_path/404$',
            test_http404_view,
            name='re_path-404',
            distill_status_codes=(404,),
            distill_func=test_no_param_func),
        distill_re_path(r'^re_path/flatpage(?P<url>.+)$',
            flatpage_view,
            name='re_path-flatpage',
            distill_func=test_flatpages_func),

    ]


if settings.HAS_PATH:
    urlpatterns += [

        distill_path('path/',
            test_no_param_view,
            name='path-no-param',
            distill_func=test_no_param_func,
            distill_file='test'),
        distill_path('path-no-func/',
            test_no_param_view,
            name='path-no-param-no-func',
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
        distill_path('path/ignore-sessions',
            test_session_view,
            name='path-ignore-sessions',
            distill_func=test_no_param_func),
        distill_path('path/404',
            test_http404_view,
            name='path-404',
            distill_status_codes=(404,),
            distill_func=test_no_param_func),
        distill_path('path/flatpage<path:url>',
            flatpage_view,
            name='path-flatpage',
            distill_func=test_flatpages_func),

    ]
