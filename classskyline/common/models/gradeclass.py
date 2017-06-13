# -*- coding: utf-8 -*-
from django.db.models import Model, CharField, IntegerField, NullBooleanField


class Gradeclass(Model):
    name = CharField(max_length=50, blank=True)
    description = CharField(max_length=200, blank=True)
    totals = IntegerField(null=True)
    seq = IntegerField(null=True)
    is_init = NullBooleanField()

