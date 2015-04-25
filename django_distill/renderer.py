# -*- coding: utf-8 -*-

from django.http import HttpRequest

class DistillRender(object):
    '''
        Renders a complete static site from all urls registered with
        distill_url() and then copies over all static media.
    '''

    def __init__(self, output_dir, urls_to_distill):
        self.output_dir = output_dir
        self.urls_to_distill = urls_to_distill
        self._counter = 0

    def __iter__(self):
        return self

    def next(self):
        try:
            u = self.urls_to_distill[self._counter]
            self._counter += 1
            print(' ', self._counter)
            return (u, '')
        except IndexError:
            raise StopIteration

# eof
