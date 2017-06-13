# -*- coding: utf-8 -*-


class VirAPIException(Exception):

    def __init__(self, *args, **kwargs):
        super(VirAPIException, self).__init__(*args, **kwargs)
