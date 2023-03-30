from datetime import timedelta
from django.conf import settings
from django.http import HttpResponse
from django.urls import include, path, reverse
from django.conf.urls.i18n import i18n_patterns
from django.shortcuts import render
from django.utils import timezone
from django.contrib.flatpages.views import flatpage as flatpage_view
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.apps import apps as django_apps
from django_distill import distill_path, distill_re_path


class TestStaticViewSitemap(Sitemap):

    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return ['path-sitemap']

    def location(self, item):
        return reverse(item)


sitemap_dict = {
    'static': TestStaticViewSitemap,
}


def test_no_param_view(request):
    return HttpResponse(b'test', content_type='application/octet-stream')


def test_positional_param_view(request, param):
    if not isinstance(param, str):
        param = str(param)
    return HttpResponse(b'test' + param.encode(),
                        content_type='application/octet-stream')


def test_named_param_view(request, param=None):
    if not isinstance(param, str):
        param = str(param)
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


def test_humanize_view(request):
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)
    nineteen_hours_ago = now - timedelta(hours=19)
    return render(request, 'humanize.html', {
        'now': now,
        'one_hour_ago': one_hour_ago,
        'nineteen_hours_ago': nineteen_hours_ago
    })


def test_no_param_func():
    return None


def test_positional_param_func():
    return ('12345', '67890')


def test_named_param_func():
    return [{'param': 'test'}]


def test_flatpages_func():
    Site = django_apps.get_model('sites.Site')
    current_site = Site.objects.get_current()
    flatpages = current_site.flatpage_set.filter(registration_required=False)
    for flatpage in flatpages:
        yield {'url': flatpage.url}


urlpatterns = [

    path('path/namespace1/',
        include('tests.namespaced_urls', namespace='test_namespace')),
    path('path/no-namespace/',
        include('tests.no_namespaced_urls')),

]


urlpatterns += i18n_patterns(
    path('path/i18n/', include('tests.i18n_urls')),
)


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
        distill_re_path(r'^re_path/x/([\d]+)$',
            test_positional_param_view,
            name='re_path-positional-param-custom',
            distill_func=test_positional_param_func,
            distill_file="re_path/x/{}.html"),
        distill_re_path(r'^re_path/(?P<param>[\w]+)$',
            test_named_param_view,
            name='re_path-named-param',
            distill_func=test_named_param_func),
        distill_re_path(r'^re_path/x/(?P<param>[\w]+)$',
            test_named_param_view,
            name='re_path-named-param-custom',
            distill_func=test_named_param_func,
            distill_file="re_path/x/{param}.html"),
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
        distill_path('path/x/<int>',
            test_positional_param_view,
            name='path-positional-param-custom',
            distill_func=test_positional_param_func,
            distill_file="path/x/{}.html"),
        distill_path('path/<str:param>',
            test_named_param_view,
            name='path-named-param',
            distill_func=test_named_param_func),
        distill_path('path/x/<str:param>',
            test_named_param_view,
            name='path-named-param-custom',
            distill_func=test_named_param_func,
            distill_file="path/x/{param}.html"),
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
        distill_path('path/test-sitemap',
            sitemap,
            {'sitemaps': sitemap_dict},
            name='path-sitemap'
        ),
        distill_path(route='path/kwargs',
            view=test_no_param_view,
            name='test-kwargs'),
        distill_path('path/humanize',
            test_humanize_view,
            name='test-humanize')

    ]
