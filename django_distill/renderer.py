import errno
import inspect
import logging
import os
import types
from shutil import copy2
from django.utils import translation
from django.conf import settings
from django.urls import include as include_urls, get_resolver
from django.core.exceptions import ImproperlyConfigured, MiddlewareNotUsed
from django.utils.module_loading import import_string
from django.test import RequestFactory
from django.test.client import ClientHandler
from django.urls import reverse, ResolverMatch
from django.urls.exceptions import NoReverseMatch
from django.core.management import call_command
from django_distill.errors import DistillError


logger = logging.getLogger(__name__)
urlconf = get_resolver()


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


def load_namespace_map():
    namespace_map = {}
    for (namespaces, url) in iter_resolved_urls(urlconf.url_patterns):
        if namespaces:
            nspath = ':'.join(namespaces)
            if url in namespace_map:
                raise DistillError(f'Ambiguous namespace for URL "{url}" in namespace '
                                   f'"{nspath}", Distill does not support the same Django '
                                   f'app being include()ed more than once in the same '
                                   f'project')
            else:
                namespace_map[url] = nspath
    return namespace_map


class DistillHandler(ClientHandler):
    '''
        Overload ClientHandler's resolve_request(...) to return the already known
        and pre-resolved view method. Also overwrite any session handling middleware
        with the dummy session handler.
    '''

    def __init__(self, *a, **k):
        self.view_func = lambda x: x
        self.view_uri_args = ()
        self.view_uri_kwargs = {}
        self.view_args = ()
        k['enforce_csrf_checks'] = False
        super().__init__(*a, *k)

    def set_view(self, view_func, view_uri_args, view_uri_kwargs, view_args):
        self.view_func = view_func
        self.view_uri_args = view_uri_args
        self.view_uri_kwargs = view_uri_kwargs
        self.view_args = view_args

    def resolve_request(self, request):
        for arg in self.view_args:
            self.view_uri_kwargs.update(**arg)
        return ResolverMatch(
            self.view_func,
            self.view_uri_args,
            self.view_uri_kwargs,
        )

    def load_middleware(self, is_async=False):
        '''
            Replaces the standard BaseHandler.load_middleware(). This method is
            identical apart from not trapping all exceptions. We actually want the
            real Python exceptions to be raised here.
        '''
        self._view_middleware = []
        self._template_response_middleware = []
        self._exception_middleware = []
        get_response = self._get_response_async if is_async else self._get_response
        handler = get_response
        handler_is_async = is_async
        for middleware_path in reversed(settings.MIDDLEWARE):
            middleware = import_string(middleware_path)
            middleware_can_sync = getattr(middleware, 'sync_capable', True)
            middleware_can_async = getattr(middleware, 'async_capable', False)
            if not middleware_can_sync and not middleware_can_async:
                raise RuntimeError(
                    'Middleware %s must have at least one of '
                    'sync_capable/async_capable set to True.' % middleware_path
                )
            elif not handler_is_async and middleware_can_sync:
                middleware_is_async = False
            else:
                middleware_is_async = middleware_can_async
            try:
                # Adapt handler, if needed.
                adapted_handler = self.adapt_method_mode(
                    middleware_is_async,
                    handler,
                    handler_is_async,
                    debug=settings.DEBUG,
                    name='middleware %s' % middleware_path,
                )
                mw_instance = middleware(adapted_handler)
            except MiddlewareNotUsed as exc:
                if settings.DEBUG:
                    if str(exc):
                        logger.debug('MiddlewareNotUsed(%r): %s', middleware_path, exc)
                    else:
                        logger.debug('MiddlewareNotUsed: %r', middleware_path)
                continue
            else:
                handler = adapted_handler
            if mw_instance is None:
                raise ImproperlyConfigured(
                    'Middleware factory %s returned None.' % middleware_path
                )
            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.insert(
                    0,
                    self.adapt_method_mode(is_async, mw_instance.process_view),
                )
            if hasattr(mw_instance, 'process_template_response'):
                self._template_response_middleware.append(
                    self.adapt_method_mode(
                        is_async, mw_instance.process_template_response
                    ),
                )
            if hasattr(mw_instance, 'process_exception'):
                self._exception_middleware.append(
                    self.adapt_method_mode(False, mw_instance.process_exception),
                )
            handler = mw_instance
            handler_is_async = middleware_is_async
        handler = self.adapt_method_mode(is_async, handler, handler_is_async)
        self._middleware_chain = handler


class DistillRender(object):
    '''
        Renders a complete static site from all urls registered with
        distill_url() and then copies over all static media.
    '''

    def __init__(self, urls_to_distill):
        self.urls_to_distill = urls_to_distill
        self.namespace_map = load_namespace_map()
        # activate the default translation
        translation.activate(settings.LANGUAGE_CODE)
        # set allowed hosts to '*', static rendering shouldn't care about the hostname
        settings.ALLOWED_HOSTS = ['*']

    def render_file(self, view_name, status_codes, view_args, view_kwargs):
        view_details = []
        for params in self.urls_to_distill:
            if view_name == params[4]:
                view_details = params
                break
        if not view_details:
            raise DistillError(f'No view exists with the name: {view_name}')
        url, distill_func, file_name, status_codes, view_name, a, k = view_details
        if view_kwargs:
            uri = self.generate_uri(url, view_name, view_kwargs)
            args = view_kwargs
        else:
            uri = self.generate_uri(url, view_name, view_args)
            args = view_args
        render = self.render_view(uri, status_codes, args, a, k)
        file_name = self._get_filename(file_name, uri, args)
        return uri, file_name, render

    def render_all_urls(self):
        for url, distill_func, file_name_base, status_codes, view_name, a, k in self.urls_to_distill:
            for param_set in self.get_uri_values(distill_func, view_name):
                if not param_set:
                    param_set = ()
                elif self._is_str(param_set):
                    param_set = (param_set,)
                uri = self.generate_uri(url, view_name, param_set)
                render = self.render_view(uri, status_codes, param_set, a, k)
                file_name = self._get_filename(file_name_base, uri, param_set)
                yield uri, file_name, render

    def render(self, view_name=None, status_codes=None, view_args=None, view_kwargs=None):
        if view_name:
            if not status_codes:
                status_codes = (200,)
            if not view_args:
                view_args = ()
            if not view_kwargs:
                view_kwargs = {}
            return self.render_file(view_name, status_codes, view_args, view_kwargs)
        else:
            return self.render_all_urls()

    def _get_filename(self, file_name, uri, param_set):
        if file_name is not None:
            if isinstance(param_set, dict):
                return file_name.format(**param_set)
            else:
                return file_name.format(*param_set)
        elif uri.endswith('/'):
            # rewrite URIs ending with a slash to ../index.html
            if uri.startswith('/'):
                uri = uri[1:]
            return uri + 'index.html'
        else:
            return None

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
        namespace = self.namespace_map.get(url, '')
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

    def render_view(self, uri, status_codes, param_set, args, kwargs={}):
        view_path, view_func = None, None
        try:
            view_path, view_func = args[0], args[1]
        except IndexError:
            try:
                view_path, view_func = kwargs['route'], kwargs['view']
            except KeyError:
                pass
        if view_path is None or view_func is None:
            raise DistillError(f'Invalid view arguments, args:{args}, kwargs:{kwargs}')
        # Default status_codes to (200,) if they are invalid or not set
        if not isinstance(status_codes, (tuple, list)):
            status_codes = (200,)
        for status_code in status_codes:
            if not isinstance(status_code, int):
                status_codes = (200,)
                break
        view_args = args[2:] if len(args) > 2 else ()
        request_factory = RequestFactory()
        request = request_factory.get(uri)
        handler = DistillHandler()
        handler.load_middleware()
        if isinstance(param_set, dict):
            a, k = (), param_set
        else:
            a, k = param_set, {}
        try:
            handler.set_view(view_func, a, k, view_args)
            response = handler.get_response(request)
        except Exception as err:
            e = 'Failed to render view "{}": {}'.format(uri, err)
            raise DistillError(e) from err
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
    call_command('collectstatic', '--noinput')
    stdout('')
    stdout('collectstatic complete, continuing...')


def filter_dirs(dirs):
    DISTILL_SKIP_ADMIN_DIRS = bool(getattr(settings, 'DISTILL_SKIP_ADMIN_DIRS', True))
    if DISTILL_SKIP_ADMIN_DIRS:
        _ignore_dirs = ('admin', 'grappelli')
    else:
        _ignore_dirs = ()
    return [d for d in dirs if d not in _ignore_dirs]


def load_urls(stdout=None):
    if stdout:
        stdout('Loading site URLs')
    for url in urlconf.url_patterns:
        include_urls(url)


def get_filepath(output_dir, file_name, page_uri):
    if file_name:
        local_uri = file_name
        full_path = os.path.join(output_dir, file_name)
    else:
        local_uri = page_uri
        if page_uri.startswith('/'):
            page_uri = page_uri[1:]
        page_path = page_uri.replace('/', os.sep)
        full_path = os.path.join(output_dir, page_path)
    return full_path, local_uri


def write_file(full_path, content):
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


def get_renderer(urls_to_distill):
    import_path = getattr(settings, "DISTILL_RENDERER", None)
    if import_path:
        render_cls = import_string(import_path)
    else:
        render_cls = DistillRender
    return render_cls(urls_to_distill)


def render_to_dir(output_dir, urls_to_distill, stdout):
    load_urls(stdout)
    renderer = get_renderer(urls_to_distill)
    for page_uri, file_name, http_response in renderer.render():
        full_path, local_uri = get_filepath(output_dir, file_name, page_uri)
        content = http_response.content
        mime = http_response.get('Content-Type')
        renamed = ' (renamed from "{}")'.format(page_uri) if file_name else ''
        msg = 'Rendering page: {} -> {} ["{}", {} bytes] {}'
        stdout(msg.format(local_uri, full_path, mime, len(content), renamed))
        write_file(full_path, content)
    return True


def render_single_file(output_dir, view_name, *args, **kwargs):
    from django_distill.distill import urls_to_distill
    status_codes = None
    if 'status_codes' in kwargs:
        status_codes = kwargs['status_codes']
        del kwargs['status_codes']
    view_name = str(view_name)
    if not status_codes:
        status_codes = (200,)
    load_urls()
    renderer = get_renderer(urls_to_distill)
    page_uri, file_name, http_response = renderer.render(
        view_name, status_codes, args, kwargs)
    full_path, local_uri = get_filepath(output_dir, file_name, page_uri)
    content = http_response.content
    write_file(full_path, content)
    return True
