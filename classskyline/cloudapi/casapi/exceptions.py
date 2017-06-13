# -*- coding: utf-8 -*-


class UnknownError(Exception):
    """未知错误"""


class HostPoolAlreadyExist(Exception):
    """主机池已存在"""


class HostPoolDoesNotExist(Exception):
    """主机池不存在"""


class MultipleHostPoolFound(Exception):
    """存在多个主机池"""


class HostAlreadyExist(Exception):
    """主机已存在"""


class HostDoesNotExist(Exception):
    """主机不存在"""


class MultipleHostFound(Exception):
    """存在多个主机"""


class VmDoesNotExist(Exception):
    """虚拟机不存在"""


class VmAlreadyExist(Exception):
    """虚拟机已存在"""


class WaitTaskTimeout(Exception):
    """等待任务超时"""

    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop('task', None)
        super(WaitTaskTimeout, self).__init__(*args, **kwargs)


class TaskDoesNotExist(Exception):
    """任务不存在"""


class VSwitchAlreadyExist(Exception):
    """虚拟交换机已存在"""


class VSwitchDoesNotExist(Exception):
    """虚拟交换机不存在"""


class NppAlreadyExist(Exception):
    """网络策略模板已存在"""


class NppDoesNotExist(Exception):
    """网络策略模板不存在"""


class AclAlreadyExist(Exception):
    """ACL 已存在"""
