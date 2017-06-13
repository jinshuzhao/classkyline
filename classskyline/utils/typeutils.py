# -*- coding: utf-8 -*-
from collections import Sized, Iterable, Container


def check_isinstance(obj, cls):
    if isinstance(obj, cls):
        return obj
    raise Exception('Expected object of type: %s' % (str(cls)))


class FixedSizeContainer(Sized, Iterable, Container):

    def __init__(self, fixed_size):
        self._items = [None] * fixed_size

    def __len__(self):
        return self._items.__len__()

    def __contains__(self, value):
        if value is None:
            return False

        return value in self._items

    def __iter__(self):
        return self._items.__iter__()

    def __getitem__(self, index):
        # NB: index starts from 1
        return self._items.__getitem__(index - 1)

    def __setitem__(self, index, value):
        # NB: index starts from 1
        return self._items.__setitem__(index - 1, value)

    def __delitem__(self, index):
        # NB: index starts from 1
        return self._items.__setitem__(index - 1, None)

    def index(self, value):
        i = self._items.index(value)
        # NB: index starts from 1
        return i + 1

    def append(self, value):
        try:
            i = self._items.index(None)  # first free seat
        except ValueError:
            return -1

        self._items[i] = value
        # NB: index starts from 1
        return i + 1
