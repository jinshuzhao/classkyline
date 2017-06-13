# -*- coding: utf-8 -*-
import os
from django.conf import settings
from django.template import Library

register = Library()
VERSION = 'E0102H01'


@register.filter('get_app_version')
def get_app_version(value):
    return VERSION

