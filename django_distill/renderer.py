# -*- coding: utf-8 -*-

import sys
import types

from django.utils import (six, translation)
from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory
from django.core.urlresolvers import reverse

from errors import (DistillError, DistillWarning)

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
        for distill_func, view_name, args, kwargs in self.urls_to_distill:
            for param_set in self.get_uri_values(distill_func):
                if self._is_str(param_set):
                    param_set = param_set,
                uri = self.generate_uri(view_name, param_set)
                render = self.render_view(uri, param_set, args)
                yield uri, render

    def _is_str(self, s):
        return isinstance(s, six.string_types)

    def get_uri_values(self, func):
        try:
            v = func()
        except Exception as e:
            trace = sys.exc_info()[2]
            raise DistillError('Failed to call distill function'), None, trace
        t = type(v)
        if t in (list, tuple):
            return v
        elif t == types.GeneratorType:
            return list(v)
        else:
            raise DistillError('Distill function returned an invalid type: {}'
                .format(t))

    def generate_uri(self, view_name, param_set):
        t = type(param_set)
        if t in (list, tuple):
            uri = reverse(view_name, args=param_set)
        elif t == dict:
            uri = reverse(view_name, kwargs=param_set)
        else:
            raise DistillError('Distill function returned an invalid type: {}'
                .format(t))
        return uri

    def render_view(self, uri, param_set, args):
        if len(args) < 2:
            raise DistillError('Invalid view arguments')
        view_regex, view_func = args[0], args[1]
        request_factory = RequestFactory()
        request = request_factory.get(uri)
        if type(param_set) == dict:
            a, k = (), param_set
        else:
            a, k = param_set, {}
        response = view_func(request, *a, **k)
        if self._is_str(response):
            response = HttpResponse(response)
        else:
            response.render()
        if response.status_code != 200:
            raise DistillError('View returned a non-200 status code: {}'
                .format(response.status_code))
        return response

# eof
