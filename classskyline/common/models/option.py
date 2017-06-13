# -*- coding: utf-8 -*-
from django.db.models import Model, CharField
from common.models.fields.pickle import UnicodePickledObjectField


class Option(Model):

    # TODO pre-defined key here

    key = CharField(max_length=64, unique=True)
    value = UnicodePickledObjectField()

    def __unicode__(self):
        return u'<{}: [KEY:{}, VALUE:{}]>'.format(self.__class__.__name__, self.key, self.value)
