# -*- coding: utf-8 -*-


import os
import sys
import types
import errno
from shutil import copy2


from future.utils import raise_from


from django.utils import (six, translation)
from django.conf import settings
from django.conf.urls import include as include_urls
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.test import RequestFactory
from django.urls import reverse
from django.core.management import call_command


from django_distill.errors import (DistillError, DistillWarning)


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
        for distill_func, file_name, view_name, a, k in self.urls_to_distill:
            for param_set in self.get_uri_values(distill_func):
                if not param_set:
                    param_set = ()
                elif self._is_str(param_set):
                    param_set = param_set,
                uri = self.generate_uri(view_name, param_set)
                render = self.render_view(uri, param_set, a)
                # rewrite URIs ending with a slash to ../index.html
                if file_name is None and uri.endswith('/'):
                    if uri.startswith('/'):
                        uri = uri[1:]
                    yield uri, uri + 'index.html', render
                    continue
                yield uri, file_name, render

    def _is_str(self, s):
        return isinstance(s, six.string_types)

    def get_uri_values(self, func):
        try:
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

    def generate_uri(self, view_name, param_set):
        if isinstance(param_set, (list, tuple)):
            uri = reverse(view_name, args=param_set)
        elif isinstance(param_set, dict):
            uri = reverse(view_name, kwargs=param_set)
        else:
            err = 'Distill function returned an invalid type: {}'
            raise DistillError(err.format(type(param_set)))
        return uri

    def render_view(self, uri, param_set, args):
        if len(args) < 2:
            raise DistillError('Invalid view arguments')
        view_regex, view_func = args[0], args[1]
        request_factory = RequestFactory()
        request = request_factory.get(uri)
        if isinstance(param_set, dict):
            a, k = (), param_set
        else:
            a, k = param_set, {}
        try:
            response = view_func(request, *a, **k)
        except Exception as err:
            e = 'Failed to render view: {}'.format(err)
            raise_from(DistillError(e), err)
        if self._is_str(response):
            response = HttpResponse(response)
        elif isinstance(response, TemplateResponse):
            response.render()
        if response.status_code != 200:
            err = 'View returned a non-200 status code: {}'
            raise DistillError(err.format(response.status_code))
        return response

    def copy_static(self, dir_from, dir_to):
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


def run_collectstatic(stdout):
    stdout('Distill is running collectstatic...')
    call_command('collectstatic')
    stdout('')
    stdout('collectstatic complete, continuing...')


_ignore_dirs = ('admin', 'grappelli')


def filter_dirs(dirs):
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
            if page_uri.startswith(os.sep):
                page_uri = page_uri[1:]
            full_path = os.path.join(output_dir, page_uri)
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
    static_url = settings.STATIC_URL
    static_url = static_url[1:] if static_url.startswith('/') else static_url
    static_output_dir = os.path.join(output_dir, static_url)
    for file_from, file_to in renderer.copy_static(settings.STATIC_ROOT,
                                                   static_output_dir):
        stdout('Copying static: {} -> {}'.format(file_from, file_to))
    media_url = settings.MEDIA_URL
    if settings.MEDIA_ROOT:
        media_url = media_url[1:] if media_url.startswith('/') else media_url
        media_output_dir = os.path.join(output_dir, media_url)
        for file_from, file_to in renderer.copy_static(settings.MEDIA_ROOT,
                                                       media_output_dir):
            stdout('Copying media: {} -> {}'.format(file_from, file_to))
    return True


# eof
