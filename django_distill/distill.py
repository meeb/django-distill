# -*- coding: utf-8 -*-

from django.conf.urls import url

urls_to_distill = []

def distill_url(*a, **k):
    distill = k.get('distill')
    if distill:
        del k['distill']
        urls_to_distill.append((distill, a, k))
    return url(*a, **k)

# eof
