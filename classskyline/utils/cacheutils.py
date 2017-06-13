# -*- coding: utf-8 -*-
import logging

from django.core.cache import get_cache
from common.models import Terminal, Course, Desktop, Classroom
from utils import fileutils
from utils import settingsutils
from utils.fileutils import import_license, generate_trail
from utils.typeutils import FixedSizeContainer
from utils.settingsutils import OptsMgr, ACTIVATION_LICENSE, ACTIVATION_TRAIL, TERMINAL_NUMBERS

LOG = logging.getLogger(__name__)
CACHE = get_cache('default')
""":type : django.core.cache.backends.locmem.LocMemCache"""


def get_terminal(tmac):
    key = 'TERMINAL:%s' % tmac
    value = CACHE.get(key)
    if value is None:
        try:
            value = Terminal.objects.get(mac_address=tmac)
            CACHE.set(key, value)
            LOG.debug('read %s[%s] from db' % (key, value))
        except Terminal.DoesNotExist:
            pass
    else:
        LOG.debug('read %s[%s] from cache' % (key, value))
    return value


def get_or_create_terminal(tmac, tname, tip):
    value = get_terminal(tmac)
    if value is None:
        key = 'TERMINAL:%s' % tmac
        value = Terminal.objects.create(name=tname, ip_address=tip, mac_address=tmac)
        CACHE.set(key, value)
    return value


def clear_terminal(tmac):
    key = 'TERMINAL:%s' % tmac
    if CACHE.has_key(key):
        CACHE.delete(key)


def get_classroom(name='default'):  # FIXME default classroom id is 1
    key = 'CLASSROOM:%s' % name
    value = CACHE.get(key)
    if value is None:
        try:
            value = Classroom.objects.get(name=name)
            CACHE.set(key, value)
            LOG.debug('read %s[%s] from db' % (key, value))
        except Classroom.DoesNotExist:
            pass
    else:
        LOG.debug('read %s[%s] from cache' % (key, value))
    return value


def clear_classroom(name='default'):
    key = 'CLASSROOM:%s' % name
    if CACHE.has_key(key):
        CACHE.delete(key)


def get_course(cuuid):
    key = 'COURSE:%s' % cuuid
    value = CACHE.get(key)
    if value is None:
        try:
            value = Course.objects.get(uuid=cuuid)
            CACHE.set(key, value)
            LOG.debug('read %s[%s] from db' % (key, value))
        except Course.DoesNotExist:
            pass
    else:
        LOG.debug('read %s[%s] from cache' % (key, value))
    return value


def clear_course(course):
    key = 'COURSE:%s' % course.uuid
    if CACHE.has_key(key):
        CACHE.delete(key)


def get_desktop(course, name):
    key = 'DESKTOP:%s:%s' % (course.pk, name)
    value = CACHE.get(key)
    if value is None:
        try:
            value = Desktop.objects.get(course=course, name=name)
            CACHE.set(key, value)
            LOG.debug('read %s[%s] from db' % (key, value))
        except Desktop.DoesNotExist:
            pass
    else:
        LOG.debug('read %s[%s] from cache' % (key, value))
    return value


def clear_desktop(desktop):
    key = 'DESKTOP:%s:%s' % (desktop.course.pk, desktop.name)
    if CACHE.has_key(key):
        CACHE.delete(key)


def get_license():
    key = 'ACTIVATION:LICENSE'
    value = CACHE.get(key)
    if value is None:
        data = OptsMgr.get_value(ACTIVATION_LICENSE)
        if data:
            value = import_license(data)
            CACHE.set(key, value)
            LOG.debug('read %s[%s] from db' % (key, value))
    else:
        LOG.debug('read %s[%s] from cache' % (key, value))
    return value


def clear_license():
    key = 'ACTIVATION:LICENSE'
    if CACHE.has_key(key):
        CACHE.delete(key)


def get_trail():
    key = 'ACTIVATION:TRAIL'
    value = CACHE.get(key)
    if value is None:
        data = OptsMgr.get_value(ACTIVATION_TRAIL)
        if data:
            value = fileutils.get_trail_days(data)
            CACHE.set(key, value)
            LOG.debug('read %s[%s] from db' % (key, value))
        else:
            trail = generate_trail()
            OptsMgr.set_value(ACTIVATION_TRAIL, trail)
            value = fileutils.get_trail_days(trail)
            CACHE.set(key, value)
    else:
        LOG.debug('read %s[%s] from cache' % (key, value))
    return value


def get_nics():
    key = 'ACTIVATION:NICS'
    value = CACHE.get(key)
    if value is None:
        from utils.sysutils import get_nic_macs
        value = get_nic_macs()
        CACHE.set(key, value)
        LOG.debug('read %s[%s] from system' % (key, value))
    else:
        LOG.debug('read %s[%s] from cache' % (key, value))
    return value


def get_tns():
    key = 'TERMINAL:NUMBERS'
    value = CACHE.get(key)
    """:type : utils.typeutils.FixedSizeContainer"""
    if value is None:
        value = OptsMgr.get_value(TERMINAL_NUMBERS)
        if value is None:
            value = FixedSizeContainer(settingsutils.get_max_users())
        CACHE.get(key, value)
        LOG.debug('read %s[%s] from db' % (key, value))
    else:
        LOG.debug('read %s[%s] from cache' % (key, value))
    return value


def clear_tns():
    key = 'TERMINAL:NUMBERS'
    if CACHE.has_key(key):
        CACHE.delete(key)
