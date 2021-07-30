import os
import sys
import inspect
import types
import errno
import warnings
from shutil import copy2
from django.utils import translation
from django.conf import settings
from django.conf.urls import include as include_urls
from django.http import HttpResponse
from django.template.response import SimpleTemplateResponse
from django.test import RequestFactory
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.core.management import call_command
from django_distill.errors import DistillError, DistillWarning


namespace_map = {}
urlconf = __import__(settings.ROOT_URLCONF, {}, {}, [''])


def iter_resolved_urls(url_patterns, namespace_path=[]):
    url_patterns_resolved = []
    for entry in url_patterns:
        if hasattr(entry, 'url_patterns'):
            if getattr(entry, 'namespace', None) is not None:
                url_patterns_resolved += iter_resolved_urls(
                    entry.url_patterns, namespace_path + [entry.namespace])
            else:
                url_patterns_resolved += iter_resolved_urls(
                    entry.url_patterns, namespace_path)
        else:
            url_patterns_resolved.append((namespace_path, entry))
    return url_patterns_resolved


for (namespaces, url) in iter_resolved_urls(urlconf.urlpatterns):
    if namespaces:
        nspath = ':'.join(namespaces)
        if url in namespace_map:
            raise DistillError(f'Ambiguous namespace for URL "{url}" in namespace '
                               f'"{nspath}", Distill does not support the same Django '
                                'app being include()ed more than once in the same '
                                'project')
        else:
            namespace_map[url] = nspath


class DummyInterface:
    '''
        Implements a dummy interface which raises a warning if any attributes or
        methods are accessed. This is used to replace specific non-implemented features,
        like sessions, which may be in end users site code but has no relevance for
        a static site and can be ignored. As this may be a non-obvious breaking change
        to a users site display a descriptive warning when rendering.
    '''

    _err = ('{}.{}({}, {}) called. This is a dummy interface. The {} feature of Django '
            'is not supported by distill. This request will do nothing and has no '
            'effect when rendering a static site. If this request is a requirement for '
            'the function of your site when it is not being rendered you can ignore '
            'this warning.')

    def __init__(self, name):
        self._name = name

    def __getattribute__(self, attr, *args, **kwargs):
        if attr.startswith('_'):
            return object.__getattribute__(self, attr)
        def _dummy_func(*args, **kwargs):
            warnings.warn(self._err.format(self._name, attr, args, kwargs, self._name),
                          RuntimeWarning)
            return lambda x: x
        return _dummy_func

    def __getitem__(self, key):
        warnings.warn(self._err.format(self._name, '__getitem__', key, {}, self._name),
                      RuntimeWarning)

    def __setitem__(self, key, value):
        warnings.warn(self._err.format(self._name, '__setitem__', (key, value), {},
                      self._name), RuntimeWarning)

    def __delitem__(self, key):
        warnings.warn(self._err.format(self._name, '__delitem__', key, {}, self._name),
                      RuntimeWarning)

    def __contains__(self, key):
        warnings.warn(self._err.format(self._name, '__contains__', key, {}, self._name),
                      RuntimeWarning)


class DistillRender(object):
    '''
        Renders a complete static site from all urls registered with
        distill_url() and then copies over all static media.
    '''

    def __init__(self, output_dir, urls_to_distill):
        self.output_dir = output_dir
        self.urls_to_distill = urls_to_distill
        # activate the default translation
        translation.activate(settings.LANGUAGE_CODE)

    def render(self):
        for url, distill_func, file_name, status_codes, view_name, a, k in self.urls_to_distill:
            for param_set in self.get_uri_values(distill_func, view_name):
                if not param_set:
                    param_set = ()
                elif self._is_str(param_set):
                    param_set = param_set,
                uri = self.generate_uri(url, view_name, param_set)
                render = self.render_view(uri, status_codes, param_set, a)
                # rewrite URIs ending with a slash to ../index.html
                if file_name is None and uri.endswith('/'):
                    if uri.startswith('/'):
                        uri = uri[1:]
                    yield uri, uri + 'index.html', render
                    continue
                yield uri, file_name, render

    def _is_str(self, s):
        return isinstance(s, str)

    def get_uri_values(self, func, view_name):
        fullargspec = inspect.getfullargspec(func)
        try:
            if 'view_name' in fullargspec.args:
                v = func(view_name)
            else:
                v = func()
        except Exception as e:
            raise DistillError('Failed to call distill function: {}'.format(e))
        if not v:
            return (None,)
        elif isinstance(v, (list, tuple)):
            return v
        elif isinstance(v, types.GeneratorType):
            return list(v)
        else:
            err = 'Distill function returned an invalid type: {}'
            raise DistillError(err.format(type(v)))

    def generate_uri(self, url, view_name, param_set):
        namespace = namespace_map.get(url, '')
        view_name_ns = namespace + ':' + view_name if namespace else view_name
        if isinstance(param_set, (list, tuple)):
            try:
                uri = reverse(view_name, args=param_set)
            except NoReverseMatch:
                uri = reverse(view_name_ns, args=param_set)
        elif isinstance(param_set, dict):
            try:
                uri = reverse(view_name, kwargs=param_set)
            except NoReverseMatch:
                uri = reverse(view_name_ns, kwargs=param_set)
        else:
            err = 'Distill function returned an invalid type: {}'
            raise DistillError(err.format(type(param_set)))
        return uri

    def render_view(self, uri, status_codes, param_set, args):
        if len(args) < 2:
            raise DistillError('Invalid view arguments')
        # Default status_codes to (200,) if they are invalid or not set
        if not isinstance(status_codes, (tuple, list)):
            status_codes = (200,)
        for status_code in status_codes:
            if not isinstance(status_code, int):
                status_codes = (200,)
                break
        view_regex, view_func = args[0], args[1]
        request_factory = RequestFactory()
        request = request_factory.get(uri)
        setattr(request, 'session', DummyInterface('request.session'))
        if isinstance(param_set, dict):
            a, k = (), param_set
        else:
            a, k = param_set, {}
        try:
            response = view_func(request, *a, **k)
        except Exception as err:
            e = 'Failed to render view "{}": {}'.format(uri, err)
            raise DistillError(e) from err
        if self._is_str(response):
            response = HttpResponse(response)
        elif isinstance(response, SimpleTemplateResponse):
            response.render()
        if response.status_code not in status_codes:
            err = 'View returned an invalid status code: {} (expected one of {})'
            raise DistillError(err.format(response.status_code, status_codes))
        return response


def copy_static(dir_from, dir_to):
    # we need to ignore some static dirs such as 'admin' so this is a
    # little more complex than a straight shutil.copytree()
    if not dir_from.endswith(os.sep):
        dir_from = dir_from + os.sep
    if not dir_to.endswith(os.sep):
        dir_to = dir_to + os.sep
    for root, dirs, files in os.walk(dir_from):
        dirs[:] = filter_dirs(dirs)
        for f in files:
            from_path = os.path.join(root, f)
            base_path = from_path[len(dir_from):]
            to_path = os.path.join(dir_to, base_path)
            to_path_dir = os.path.dirname(to_path)
            if not os.path.isdir(to_path_dir):
                os.makedirs(to_path_dir)
            copy2(from_path, to_path)
            yield from_path, to_path


def copy_static_and_media_files(output_dir, stdout):
    static_url = str(settings.STATIC_URL)
    static_root = str(settings.STATIC_ROOT)
    static_url = static_url[1:] if static_url.startswith('/') else static_url
    static_output_dir = os.path.join(output_dir, static_url)
    for file_from, file_to in copy_static(static_root, static_output_dir):
        stdout('Copying static: {} -> {}'.format(file_from, file_to))
    media_url = str(settings.MEDIA_URL)
    media_root = str(settings.MEDIA_ROOT)
    if media_root:
        media_url = media_url[1:] if media_url.startswith('/') else media_url
        media_output_dir = os.path.join(output_dir, media_url)
        for file_from, file_to in copy_static(media_root, media_output_dir):
            stdout('Copying media: {} -> {}'.format(file_from, file_to))
    return True


def run_collectstatic(stdout):
    stdout('Distill is running collectstatic...')
    call_command('collectstatic')
    stdout('')
    stdout('collectstatic complete, continuing...')


def filter_dirs(dirs):
    DISTILL_SKIP_ADMIN_DIRS = bool(getattr(settings, 'DISTILL_SKIP_ADMIN_DIRS', True))
    if DISTILL_SKIP_ADMIN_DIRS:
        _ignore_dirs = ('admin', 'grappelli')
    else:
        _ignore_dirs = ()
    return [d for d in dirs if d not in _ignore_dirs]


def load_urls(stdout):
    stdout('Loading site URLs')
    site_urls = getattr(settings, 'ROOT_URLCONF')
    if site_urls:
        include_urls(site_urls)


def render_to_dir(output_dir, urls_to_distill, stdout):
    mimes = {}
    load_urls(stdout)
    renderer = DistillRender(output_dir, urls_to_distill)
    for page_uri, file_name, http_response in renderer.render():
        if file_name:
            local_uri = file_name
            full_path = os.path.join(output_dir, file_name)
        else:
            local_uri = page_uri
            if page_uri.startswith('/'):
                page_uri = page_uri[1:]
            page_path = page_uri.replace('/', os.sep)
            full_path = os.path.join(output_dir, page_path)
        content = http_response.content
        mime = http_response.get('Content-Type')
        renamed = ' (renamed from "{}")'.format(page_uri) if file_name else ''
        msg = 'Rendering page: {} -> {} ["{}", {} bytes] {}'
        stdout(msg.format(local_uri, full_path, mime, len(content), renamed))
        try:
            dirname = os.path.dirname(full_path)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            with open(full_path, 'wb') as f:
                f.write(content)
        except IOError as e:
            if e.errno == errno.EISDIR:
                err = ('Output path: {} is a directory! Try adding a '
                       '"distill_file" arg to your distill_url()')
                raise DistillError(err.format(full_path))
            else:
                raise
        mimes[full_path] = mime.split(';')[0].strip()
    return True
