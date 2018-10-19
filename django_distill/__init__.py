# -*- coding: utf-8 -*-


__version__ = 1.6


from django import __version__ as django_version


from django_distill.errors import DistillError


try:
    from django_distill.distill import distill_url
except ImportError:
    def distill_url(*args, **kwargs):
        err = ('Your installed version of Django ({}) does not supprt '
               'django.urls.url or django.conf.urls.url, use '
               'django_distill.distill_re_path or django_distill.distill_path')
        raise DistillError(err.format(django_version))


try:
    from django_distill.distill import distill_re_path
except ImportError:
    def distill_re_path(*args, **kwargs):
        err = ('Your installed version of Django ({}) does not supprt '
               'django.urls.re_path, please upgrade')
        raise DistillError(err.format(django_version))


try:
    from django_distill.distill import distill_path
except ImportError:
    def distill_path(*args, **kwargs):
        err = ('Your installed version of Django ({}) does not supprt '
               'django.urls.path, please upgrade')
        raise DistillError(err.format(django_version))


# eof
