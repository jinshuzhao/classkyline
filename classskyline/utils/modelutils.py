# -*- coding: utf-8 -*-
import base64
import logging
import pickle

from django.db.models import TextField
from django.utils import six
import zlib

LOG = logging.getLogger(__name__)


def compress(value):
    return base64.b64encode(zlib.compress(value))


def decompress(value):
    return zlib.decompress(base64.b64decode(value))


class GzippedDictField(TextField):

    def to_python(self, value):
        if isinstance(value, six.string_types) and value:
            try:
                value = pickle.loads(decompress(value))
            except:
                LOG.exception('Failed to decompress dict from field')
                return {}
        elif not value:
            return {}
        return value

    def get_prep_value(self, value):
        if not value and self.null:
            return None
        # enforce unicode strings to guarantee consistency
        if isinstance(value, str):
            value = six.text_type(value)
        return compress(pickle.dumps(value))

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)
