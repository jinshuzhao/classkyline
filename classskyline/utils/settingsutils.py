# -*- coding: utf-8 -*-
#import psutil
from django.conf import settings
from django.utils.functional import curry

from common.models import Option


CAS_ADDRESS = 'CAS_ADDRESS'
CAS_USERNAME = 'CAS_USERNAME'
CAS_PASSWORD = 'CAS_PASSWORD'
CAS_HOSTPOOL = 'CAS_HOSTPOOL'
SSH_ADDRESS = 'SSH_ADDRESS'
SSH_USERNAME = 'SSH_USERNAME'
SSH_PASSWORD = 'SSH_PASSWORD'
VSWITCH_ID = 'VSWITCH_ID'
VSWITCH_NAME = 'VSWITCH_NAME'
NPP_ID = 'NPP_ID'
NPP_NAME = 'NPP_NAME'
VLAN_TAG = 'VLAN_TAG'
ACL_ID = 'ACL_ID'
ACL_NAME = 'ACL_NAME'
ACL_WHITELIST = 'ACL_WHITELIST'
INITIALIZED = 'INITIALIZED'
ACTIVATION_LICENSE = 'ACTIVATION_LICENSE'
ACTIVATION_TRAIL = 'ACTIVATION_TRAIL'
TERMINAL_NUMBERS = 'TERMINAL_NUMBERS'
DESKTOP_COUNT = 'DESKTOP_COUNT'


class OptsMgr(object):

    defaults = {
        CAS_ADDRESS: settings.STACK_BACKENDS['cas']['AUTH_URL'],
        CAS_USERNAME: settings.STACK_BACKENDS['cas']['USERNAME'],
        CAS_PASSWORD: settings.STACK_BACKENDS['cas']['PWD'],
        VSWITCH_NAME: settings.DEFAULT_VSWITCH_NAME,
        NPP_NAME: settings.DEFAULT_NPP_NAME,
        VLAN_TAG: 1,  # 1 means no VLAN tag
        ACL_NAME: settings.DEFAULT_ACL_NAME,
        ACL_WHITELIST: settings.FIREWALL_WHITELIST,
    }

    def __new__(cls):
        super_new = super(OptsMgr, cls).__new__
        cls.add_to_class()
        return super_new(cls)

    @classmethod
    def add_to_class(cls):
        for k, v in cls.defaults.iteritems():
            setattr(cls, k.lower(),
                    property(curry(cls.get_value, key=k),
                             curry(cls.set_value, key=k)))

    @classmethod
    def get_value(cls, key):
        try:
            return Option.objects.get(key=key).value
        except Option.DoesNotExist:
            if key in cls.defaults:
                return cls.defaults[key]

    @classmethod
    def set_value(cls, key, value):
        Option.objects.update_or_create(defaults={'value': value}, key=key)


def get_max_users():
    from utils import cacheutils
    lic = cacheutils.get_license()
    return 70 if lic is None else lic.max_users


def get_desktop_count():
    """
    获取桌面数量
    """
    max_users = [get_max_users()]
    data = OptsMgr.get_value(DESKTOP_COUNT)
    if data:
        max_users.append(int(data))
    return min(max_users)


def get_desktop_count1(per_cores, per_memory):
    # 检查当前系统CPU、内存等资源
    physical_cores = psutil.cpu_count(logical=False)
    max_cores = physical_cores * 3

    max_memory = psutil.virtual_memory().total / 1024 / 1024  # unit: MB
    usable_memory = int(max_memory * 0.85)

    # NB: 允许冗余 5 个
    limit1 = (max_cores + 5) // per_cores
    limit2 = usable_memory // per_memory
    return min(limit1, limit2, get_desktop_count())


def get_ftp_url(request, t_type):
    """
    获取ftp的链接
    :param request: request对象
    :param t_type: ftp类型:images, isos, soft, upgrade,
    """
    ip = request.get_host().split(':')[0]
    conf = settings.FTP_CONF[t_type]
    conf['ip'] = ip
    ftp_url = settings.FTP_TMPT.format(**conf)
    return ftp_url
