# -*- coding: utf-8 -*-


from django_distill.errors import (DistillError, DistillWarning)


urls_to_distill = []


def _distill_url(func, *a, **k):
    distill_func = k.get('distill_func')
    distill_file = k.get('distill_file')
    if distill_file:
        del k['distill_file']
    if distill_func:
        del k['distill_func']
        name = k.get('name')
        if not name:
            raise DistillError('Distill function provided with no name')
        if not callable(distill_func):
            err = 'Distill function not callable: {}'
            raise DistillError(err.format(distill_func))
        urls_to_distill.append((distill_func, distill_file, name, a, k))
    else:
        e = 'URL registered with distill_url but no distill function supplied'
        raise DistillWarning(e)
    return func(*a, **k)


try:
    from django.conf.urls import url
    def distill_url(*a, **k):
        return _distill_url(url, *a, **k)
except ImportError:
    try:
        from django.urls import url
        def distill_url(*a, **k):
            return _distill_url(url, *a, **k)
    except ImportError:
        pass


try:
    from django.urls import path
    def distill_path(*a, **k):
        return _distill_url(path, *a, **k)
except ImportError:
    pass


try:
    from django.urls import re_path
    def distill_re_path(*a, **k):
        return _distill_url(re_path, *a, **k)
except ImportError:
    pass


# eof
