# -*- coding: utf-8 -*-

from django.conf.urls import url

from errors import (DistillError, DistillWarning)

urls_to_distill = []

def distill_url(*a, **k):
    distill = k.get('distill')
    if distill:
        del k['distill']
        name = k.get('name')
        if not name:
            raise DistillError('Distill function provided with no name')
        if not callable(distill):
            raise DistillError('Distill function not callable: {}'
                .format(distill))
        urls_to_distill.append((distill, name, a, k))
    else:
        e = 'URL registered with distill_url but no distill function supplied'
        raise DistillWarning(e)
    return url(*a, **k)

# eof
