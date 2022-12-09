from django_distill.errors import DistillError


urls_to_distill = []


def _distill_url(func, *a, **k):
    distill_func = k.get('distill_func')
    if distill_func:
        del k['distill_func']
    else:
        distill_func = lambda: None
    distill_file = k.get('distill_file')
    distill_status_codes = k.get('distill_status_codes')
    if distill_file:
        del k['distill_file']
    if distill_status_codes:
        del k['distill_status_codes']
    else:
        distill_status_codes = (200,)
    name = k.get('name')
    if not name:
        raise DistillError('Distill function provided with no name')
    if not callable(distill_func):
        err = 'Distill function not callable: {}'
        raise DistillError(err.format(distill_func))
    url = func(*a, **k)
    urls_to_distill.append((url, distill_func, distill_file, distill_status_codes,
                            name, a, k))
    return url


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
