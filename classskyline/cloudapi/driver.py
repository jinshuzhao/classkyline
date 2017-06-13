# -*- coding: utf-8 -*-
import logging
import threading
from django.conf import settings
from utils import importutils, typeutils


LOG = logging.getLogger(__name__)


class VirtDriver(object):

    _instance_lock = threading.Lock()

    @staticmethod
    def instance():
        if not hasattr(VirtDriver, '_instance'):
            with VirtDriver._instance_lock:
                if not hasattr(VirtDriver, '_instance'):
                    VirtDriver._instance = load_virt_driver()
        return VirtDriver._instance


def load_virt_driver(virt_driver=None):
    """加载虚拟化驱动模块

    :param virt_driver: a virt driver name to override the config opt
    :return: a VirtDriver instance
    """
    if not virt_driver:
        virt_driver = settings.VIRT_DRIVER

    if not virt_driver:
        LOG.error('Virt driver option required, but not specified')
    else:
        LOG.debug("Loading virt driver = %s" % (virt_driver ))
    try:
        driver = importutils.import_object(virt_driver)
        LOG.debug('Driver = %s ' % driver)
        return typeutils.check_isinstance(driver, VirtDriver)
    except ImportError as e:
        LOG.exception('Unable to load the virtualization driver')
