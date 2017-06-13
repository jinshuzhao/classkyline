# -*- coding: utf-8 -*-
import os
import logging
import time

import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import HTTPError

from django.conf import settings
from django.template import Context, Template

from cloudapi.casapi import exceptions
from cloudapi.casapi.exceptions import VmAlreadyExist
from utils.settingsutils import OptsMgr, CAS_ADDRESS, CAS_USERNAME, CAS_PASSWORD
try:
    from utils.vendor.sh import qemu_img, cp, shutdown
except ImportError:
    pass

LOG = logging.getLogger(__name__)
username = OptsMgr.get_value(CAS_USERNAME)
password = OptsMgr.get_value(CAS_PASSWORD)
base_url = OptsMgr.get_value(CAS_ADDRESS)


def request(method, uri, **kwargs):
    kwargs.setdefault('headers', {})
    kwargs['headers']['accept'] = 'application/json,application/xml'
    kwargs['headers']['content-type'] = 'application/xml'

    if 'auth' not in kwargs:
        kwargs.setdefault('auth', HTTPDigestAuth(username, password))

    if 'baseurl' not in kwargs:
        kwargs.setdefault('baseurl', base_url)

    data = kwargs.get('data')
    if data:
        if isinstance(data, unicode):
            kwargs['data'] = data.encode("utf-8")

    url = kwargs.get('baseurl', base_url) + uri
    if 'baseurl' in kwargs:
        kwargs.pop('baseurl')

    r = requests.request(method, url, **kwargs)

    if r.status_code >= 400:  # log bad request
        LOG.error('Failed to %s %s, status: %d, headers: %s, content: %s' % (
            method, url, r.status_code, r.headers, r.content))
    if r.status_code == 409:
        error_code = r.headers.get('error-code')
        if error_code == '11':
            raise exceptions.UnknownError()
        elif error_code == '301':
            raise exceptions.HostPoolAlreadyExist()
        elif error_code == '304':
            raise exceptions.HostPoolDoesNotExist()
        elif error_code == '401':
            raise exceptions.HostAlreadyExist()
        elif error_code == '402':
            raise exceptions.HostDoesNotExist()
        elif error_code == '603':
            raise exceptions.VSwitchDoesNotExist()
        elif error_code == '1001':
            raise exceptions.VmDoesNotExist()
        elif error_code == '1002':
            raise exceptions.VmAlreadyExist()
        elif error_code == '1121':
            raise exceptions.NppAlreadyExist()
        elif error_code == '1130':
            raise exceptions.VSwitchAlreadyExist()
        elif error_code == '1151':
            raise exceptions.AclAlreadyExist()
    r.raise_for_status()  # raise other errors
    return r


def wait_for_task(task_id, interval=1, timeout=None):
    seconds_started = time.time()
    while True:
        try:
            r = request('get', '/cas/casrs/message/%s' % task_id)
            task_info = r.json()
            if task_info[u'completed'] == u'true':
                return task_info
            elif timeout:
                seconds_passed = time.time() - seconds_started
                if seconds_passed >= timeout:
                    raise exceptions.WaitTaskTimeout(task=task_info)
        except HTTPError as ex:
            if ex.response.status_code == 404:
                return exceptions.TaskDoesNotExist()
            raise  # re-raise exception exclude 404 (Not Found)
        time.sleep(interval)


def get_hps():
    """获取主机池列表

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_hps()
      [{u'childNum': u'1',
        u'id': u'1',
        u'name': u'vmspool',
        u'operatorGroupCode': u'00',
        u'operatorGroupId': u'1'}]
    """
    r = request('get', '/cas/casrs/hostpool/all')
    hps = r.json()[u'hostPool']
    if not isinstance(hps, list):
        hps = [hps]
    return hps


def get_hostpool():
    """获取主机池。

    :raise HostPoolDoesNotExist: 主机池不存在
    :raise MultipleHostPoolFound: 存在多个主机池
    """
    hps = get_hps()
    num = len(hps)
    if num == 1:
        return hps[0]
    if not num:
        raise exceptions.HostPoolDoesNotExist()
    raise exceptions.MultipleHostPoolFound(u'%s found!' % hps)


def create_hostpool(hpname):
    request('post', '/cas/casrs/hostpool/add/%s' % hpname)


def get_hosts(**kwargs):
    """获取主机列表

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_hosts()
      [{u'@type': u'kvm',
        u'id': u'6',
        u'ip': u'10.88.16.98',
        u'name': u'cvknode'}]
    """
    r = request('get', '/cas/casrs/host/', **kwargs)
    hosts = r.json()[u'host']
    if not isinstance(hosts, list):
        hosts = [hosts]
    return hosts


def get_host(**kwargs):
    """获取主机。

    :raise HostDoesNotExist: 主机不存在
    :raise MultipleHostFound: 存在多个主机
    """
    hosts = get_hosts(**kwargs)
    num = len(hosts)
    if num == 1:
        return hosts[0]
    if not num:
        raise exceptions.HostDoesNotExist()
    raise exceptions.MultipleHostFound('%s found!' % hosts)


def create_host(hpid, name, user, pwd, wait=False):
    c = Context({
        'user': user,
        'pwd': pwd,
        'hpid': hpid,
        'name': name,
    })
    t = Template(u'''
    <host>
      <user>{{ user }}</user>
      <pwd>{{ pwd }}</pwd>
      <hostPoolId>{{ hpid }}</hostPoolId>
      <clusterId></clusterId>
      <name>{{ name }}</name>
      <enableHA>0</enableHA>
      <ignore>false</ignore>
    </host>''')
    r = request('post', '/cas/casrs/host/add', data=t.render(c))
    task_info = r.json()
    if wait:
        task_id = task_info['msgId']
        task_info = wait_for_task(task_id)
    return task_info


def get_host_info(hostid):
    """获取主机信息

    Usage:

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_host_info(hostid=6)
      {u'@type': u'kvm',
       u'cpuCores': u'4',
       u'cpuCount': u'8',
       u'cpuFrequence': u'2400',
       u'cpuModel': u'Intel(R) Xeon(R) CPU E5-2609 0 @ 2.40GHz',
       u'cpuSockets': u'2',
       u'diskSize': u'799505',
       u'id': u'6',
       u'ip': u'10.88.16.98',
       u'memorySize': u'168967',
       u'model': u'FlexServer R390',
       u'name': u'cvknode',
       u'pNIC': [{u'description': u'Broadcom Corporation NetXtreme BCM5719 Gigabit Ethernet PCIe',
                  u'macAddr': u'2c:44:fd:7f:9f:3c',
                  u'name': u'eth0',
                  u'status': u'1'},
                 {u'description': u'Broadcom Corporation NetXtreme BCM5719 Gigabit Ethernet PCIe',
                  u'macAddr': u'2c:44:fd:7f:9f:3d',
                  u'name': u'eth1',
                  u'status': u'0'},
                 {u'description': u'Broadcom Corporation NetXtreme BCM5719 Gigabit Ethernet PCIe',
                  u'macAddr': u'2c:44:fd:7f:9f:3e',
                  u'name': u'eth2',
                  u'status': u'0'},
                 {u'description': u'Broadcom Corporation NetXtreme BCM5719 Gigabit Ethernet PCIe',
                  u'macAddr': u'2c:44:fd:7f:9f:3f',
                  u'name': u'eth3',
                  u'status': u'0'}],
       u'vendor': u'H3C'}
    """
    r = request('get', '/cas/casrs/host/id/%s' % hostid)
    return r.json()


def get_host_summary(hostid):
    """获取主机概要。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_host_summary(6)
      {u'CPU\u4e3b\u9891': u'2.4GHz',
       u'CPU\u578b\u53f7': u'Intel(R) Xeon(R) CPU E5-2609 0 @ 2.40GHz',
       u'CPU\u6570\u91cf': u'2 * 4 \u6838',
       u'IP\u5730\u5740': u'10.88.16.98',
       u'diskRate': u'23.0',
       u'image': u'1',
       u'run': u'1',
       u'shutoff': u'10',
       u'total': u'11',
       u'\u4e3b\u673a\u578b\u53f7': u'H3C FlexServer R390',
       u'\u4e3b\u673a\u672c\u5730\u5b58\u50a8': u'780.77GB',
       u'\u5185\u5b58': u'165.00GB',
       u'\u7248\u672c': u'CVK 2.0 (E0218)',
       u'\u7cfb\u7edf\u8fd0\u884c\u65f6\u95f4': u'20\u592922\u65f644\u520618\u79d2'}

    """
    r = request('get', '/cas/casrs/host/summary/%s' % hostid)
    kvs = r.json()[u'keyValue']
    if not isinstance(kvs, list):
        kvs = [kvs]
    summary = {}
    for kv in kvs:
        k = kv[u'key']
        v = kv.get(u'value')
        summary[k] = v
    return summary


def get_all_vms_of_host(host_id, offset=0, limit=0):
    url = '/cas/casrs/vm/vmList?hostId={host_id}'.format(host_id=host_id)
    if offset >= 0:
        url += '&offset={offset}'.format(offset=offset)
        if limit > 0:
            url += '&limit={limit}'.format(limit=limit)
    vms = []
    try:
        r = request('get', url)
        vms = r.json()['domain']
        if not isinstance(vms, list):
            vms = [vms]
    except HTTPError:
        pass
    return vms


def get_vms_by_name_suffix(hostid, suffix):
    vms = get_all_vms_of_host(hostid)
    return [x for x in vms if x['name'].endswith(suffix)]


def get_vms_by_name(hostid, name):
    vms = get_all_vms_of_host(hostid)
    for x in vms:
        if x['name'] == name:
            return x


def get_all_profiles(**kwargs):
    """获取网络策略模板列表。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_all_profiles()
      [{u'aclName': u'defaultacl',
        u'aclStrategyId': u'1',
        u'enableVlan': u'0',
        u'enableVsi': u'0',
        u'id': u'1',
        u'inbound': u'0',
        u'name': u'Default',
        u'outbound': u'0',
        u'type': u'0',
        u'vlanId': u'1',
        u'vnetPriority': u'0',
        u'vsiIdFormat': u'UUID'}]

    """
    r = request('get', '/cas/casrs/profile/', **kwargs)
    profiles = r.json()['portProfile']
    if not isinstance(profiles, list):
        profiles = [profiles]
    return profiles


def get_host_monitor(hostid):
    """获取主机性能信息。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_host_monitor(6)
      {u'cpuRate': u'2.89',
       u'disk': [{u'device': u'sda1', u'usage': u'23.0'},
                 {u'device': u'sda5', u'usage': u'1.0'},
                 {u'device': u'sda7', u'usage': u'7.0'},
                 {u'device': u'sdb', u'usage': u'55.0'}],
       u'memRate': u'4.02'}

    """
    r = request('get', '/cas/casrs/host/id/%s/monitor' % hostid)
    return r.json()


def get_vm_info(vmid):
    """获取虚拟机信息

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_vm_info(1416)
      {u'auto': u'0',
       u'autoBooting': u'0',
       u'bootingDevice': u'1',
       u'cpu': u'1',
       u'createDate': u'2015-09-07T16:22:57+08:00',
       u'deployed': u'false',
       u'description': u'????',
       u'existBlock': u'false',
       u'existCdromOrFloppy': u'false',
       u'existPciOrUsb': u'false',
       u'existRaw': u'false',
       u'flag': u'1',
       u'hostId': u'6',
       u'hostPoolId': u'1',
       u'hoststatus': u'0',
       u'id': u'1416',
       u'memory': u'2048',
       u'name': u'wins7.base',
       u'network': [{u'ipAddr': u'10.88.16.219',
                     u'isLimitInBound': u'false',
                     u'isLimitOutBound': u'false',
                     u'mac': u'0c:da:41:1d:3b:02',
                     u'mode': u'VEB',
                     u'virtualport': u'false',
                     u'vlan': u'1',
                     u'vsName': u'vswitch0'}],
       u'osBit': u'x86_64',
       u'status': u'2',
       u'storage': [{u'capacity': u'20480',
                     u'device': u'vda',
                     u'diskDevice': u'\u78c1\u76d8',
                     u'storeFile': u'/vms/ssd/wins7.base',
                     u'targetBus': u'virtio',
                     u'type': u'file'}],
       u'system': u'0',
       u'title': u'wins7.base',
       u'type': u'0',
       u'uuid': u'e924bce5-8f96-4eee-98fe-f84aae8f6d50'}

    """
    r = request('get', '/cas/casrs/vm/%s' % vmid)
    vm_info = r.json()
    networks = vm_info[u'network']
    if not isinstance(networks, list):
        vm_info[u'network'] = [networks]
    storages = vm_info[u'storage']
    if not isinstance(storages, list):
        vm_info[u'storage'] = [storages]
    return vm_info


def get_vm_summary(vmid):
    """获取虚拟机概要

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_vm_summary(1416)
      {u'CAS Tools': u'\u672a\u8fd0\u884c',
       u'CPU\u5229\u7528\u7387': u'10.49586776859504',
       u'CPU\u8c03\u5ea6\u4f18\u5148\u7ea7': u'\u9ad8',
       u'HA\u5f02\u5e38\u72b6\u6001': u'0',
       u'I/O\u4f18\u5148\u7ea7': u'\u9ad8',
       u'UUID': u'e924bce5-8f96-4eee-98fe-f84aae8f6d50',
       u'VNC\u7aef\u53e3': u'5903',
       u'system': u'0',
       u'\u4e3b\u673a': u'cvknode(10.88.16.98)',
       u'\u4f53\u7cfb\u7ed3\u6784': u'x86_64',
       u'\u4fdd\u62a4\u6a21\u5f0f': u'\u4e0d\u542f\u7528',
       u'\u5185\u5b58': u'2.00GB',
       u'\u5185\u5b58\u5229\u7528\u7387': u'100.0',
       u'\u5185\u5b58\u8d44\u6e90\u4f18\u5148\u7ea7': u'\u4f4e',
       u'\u521b\u5efa\u65f6\u95f4': u'2015-09-07 16:22:57',
       u'\u542f\u7528VNC\u4ee3\u7406': u'\u5426',
       u'\u5b58\u50a8': u'20.00GB',
       u'\u63a7\u5236\u53f0': u'VNC',
       u'\u63cf\u8ff0': u'????',
       u'\u64cd\u4f5c\u7cfb\u7edf': None,
       u'\u663e\u793a\u540d\u79f0': u'wins7.base',
       u'\u7269\u7406\u5730\u5740\u6269\u5c55\uff08PAE\uff09': u'\u662f',
       u'\u72b6\u6001': u'running',
       u'\u81ea\u52a8\u8fc1\u79fb': u'\u5426',
       u'\u81ea\u52a8\u914d\u7f6e': u'\u662f',
       u'\u865a\u62dfCPU': u'1',
       u'\u9ad8\u53ef\u9760\u6027': u'1',
       u'\u9ad8\u7ea7\u53ef\u7f16\u7a0b\u4e2d\u65ad\u63a7\u5236\u5668\uff08APIC\uff09': u'\u662f',
       u'\u9ad8\u7ea7\u914d\u7f6e\u4e0e\u7535\u6e90\u7ba1\u7406\u63a5\u53e3\uff08ACPI\uff09': u'\u662f'}
    """
    r = request('get', '/cas/casrs/vm/%s/summary' % vmid)
    kvs = r.json()[u'keyValue']
    if not isinstance(kvs, list):
        kvs = [kvs]
    summary = {}
    for kv in kvs:
        k = kv[u'key']
        v = kv.get(u'value')
        summary[k] = v
    return summary


def get_vm_network(vmid):
    """获取虚拟机网络

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_vm_network(1416)
      {u'ipAddr': u'10.88.16.219',
       u'isLimitInBound': u'false',
       u'isLimitOutBound': u'false',
       u'mac': u'0c:da:41:1d:3b:02',
       u'mode': u'VEB',
       u'virtualport': u'false',
       u'vlan': u'1',
       u'vsName': u'vswitch0'}

    """
    r = request('get', '/cas/casrs/vm/network/%s' % vmid)
    networks = r.json()['network']
    if not isinstance(networks, list):
        networks = [networks]
    return networks


def get_vm_ipaddrs(vmid):
    networks = get_vm_network(vmid)
    ipaddrs = [x['ipAddr'] for x in networks if x.has_key('ipAddr')]
    return ipaddrs


def get_vswitch_info(hostid, vswitch_name):
    vss = get_all_vswitches(hostid)
    for vs in vss:
        if vs['name'] == vswitch_name:
            return vs
    LOG.error('Failed to find vswitch %s' % vswitch_name)
    raise exceptions.VSwitchDoesNotExist()


def get_npp_info(npp_name, **kwargs):
    npps = get_all_profiles(**kwargs)
    for npp in npps:
        if npp['name'] == npp_name:
            return npp
    LOG.error('Failed to find network policy profile %s' % npp_name)
    raise exceptions.NppDoesNotExist()


def get_vm_by_host(hostid, vmname):
    r = request('get', '/cas/casrs/vm/vmList?hostId=%s&domainName=%s' % (
        hostid, vmname))
    return r.json()['domain']


def get_all_vswitches(hostid, **kwargs):
    """获取虚拟交换机列表。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_all_vswitches(6)
      [{u'address': u'10.88.16.98',
        u'bondMode': u'',
        u'enableLacp': u'false',
        u'flag': u'0',
        u'gateway': u'10.88.16.1',
        u'hostId': u'6',
        u'id': u'6',
        u'isManage': u'1',
        u'isRuningVmUseVSwitch': u'false',
        u'mode': u'0',
        u'name': u'vswitch0',
        u'netmask': u'255.255.254.0',
        u'pnic': u'eth0',
        u'portNum': u'32',
        u'status': u'1'}]

    """
    r = request('get', '/cas/casrs/host/id/%s/vswitch' % hostid, **kwargs)
    vss = r.json()['vSwitch']
    if not isinstance(vss, list):
        vss = [vss]
    return vss


def get_vm_detail(vmid):
    """获取虚拟机详细信息。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_vm_detail(1416)
      {u'advance': {u'redirUsb': u'0',
                    u'spiceSet': u'false'},
       u'basic': {u'acpi': u'1',
                  u'apic': u'1',
                  u'architecture': u'X86_64',
                  u'blkiotune': u'500',
                  u'clock': u'localtime',
                  u'controller': u'1',
                  u'desc': u'????',
                  u'emulator': u'/usr/bin/kvm',
                  u'haManage': u'1',
                  u'manager': u'kvm',
                  u'osha': u'0',
                  u'pae': u'1',
                  u'timeSync': u'0'},
       u'bootDev': {u'autoStart': u'0'},
       u'cpu': {u'cpuArch': u'x86_64',
                u'cpuCores': u'1',
                u'cpuGurantee': u'0',
                u'cpuMaxRate': u'2400',
                u'cpuMinRate': u'10',
                u'cpuMode': u'custom',
                u'cpuShares': u'1024',
                u'cpuSockets': u'1',
                u'maxCpuNum': u'8'},
       u'graphics': {u'address': u'0.0.0.0',
                     u'kayboardMap': u'-',
                     u'password': u'-',
                     u'port': u'-1',
                     u'type': u'vnc'},
       u'id': u'1416',
       u'input': [{u'bus': u'usb',
                   u'model': u'absolute',
                   u'type': u'tablet'},
                  {u'bus': u'ps2',
                   u'model': u'relative',
                   u'type': u'mouse'}],
       u'memory': {u'hostMemory': u'168967',
                   u'maxMemory': u'168967',
                   u'memoryBacking': u'0',
                   u'memoryPriority': u'50',
                   u'memoryUnit': u'MB',
                   u'size': u'2048'},
       u'name': u'wins7.base',
       u'network': {u'deviceModel': u'virtio',
                    u'isKernelAccelerated': u'0',
                    u'isLimitInBound': u'false',
                    u'isLimitOutBound': u'false',
                    u'mac': u'0c:da:41:1d:3b:02',
                    u'mode': u'veb',
                    u'netType': u'0',
                    u'virtualport': u'false',
                    u'vsId': u'6',
                    u'vsMode': u'0',
                    u'vsName': u'vswitch0'},
       u'numa': {u'nodeSize': u'2'},
       u'serial': {u'port': u'0', u'type': u'pty'},
       u'storage': {u'allocation': u'9484',
                    u'cacheType': u'directsync',
                    u'device': u'disk',
                    u'deviceName': u'vda',
                    u'fileType': u'file',
                    u'format': u'qcow2',
                    u'maxSize': u'225181',
                    u'path': u'/vms/ssd/wins7.base',
                    u'size': u'20480',
                    u'snapShot': u'0',
                    u'targetBus': u'virtio'},
       u'title': u'wins7.base',
       u'videoType': u'vga'}

    """
    r = request('get', '/cas/casrs/vm/detail/%s' % vmid)
    return r.json()


def create_backing_volume(src_img, dst_img):
    options = ['create', '-b', src_img, '-o', 'cluster_size=64k', '-f', 'qcow2', dst_img]
    qemu_img(options)


def create_original_volume(fpath, capacity):
    """Create volume
    :param fpath: full path of image
    :param capacity: unit is MB
    """
    capacity = '{}M'.format(capacity)
    options = ['create', '-o', 'cluster_size=64k', '-f', 'qcow2', fpath, capacity]
    qemu_img(options)


def resize_volume(fpath, capacity):
    """Resize volume
    :param fpath: full path of image
    :param capacity: unit is MB
    """
    capacity = '{}M'.format(capacity)
    options = ['resize', fpath, capacity]
    qemu_img(options)


def create_vm_hack(hp_id, host_id, os_version, vs_id, vs_name, profile_id, vm_name, dst_img, mac_addr, cpu_count, mem_size):
    c = Context({
        'name': vm_name,
        'hp_id': hp_id,
        'host_id': host_id,
        'os_version': os_version,
        'vs_id': vs_id,
        'vs_name': vs_name,
        'profile_id': profile_id,
        'store_file': dst_img,
        'mac_addr': mac_addr,
        'cpu': cpu_count,
        'mem': mem_size
    })
    t = Template(u'''
    <domain>
        <name>{{ name }}</name>
        <title>{{ name }}</title>
        <memory>{{mem}}</memory>
        <memoryPriority>50</memoryPriority>
        <cpuSockets>1</cpuSockets>
        <cpuCores>{{cpu}}</cpuCores>
        <cpuShares>512</cpuShares>
        <maxCpuSocket>2</maxCpuSocket>
        <blkiotune>500</blkiotune>
        <system>0</system>
        <osVersion>{{ os_version }}</osVersion>
        <autoMigrate>0</autoMigrate>
        <priority>2</priority>
        <osInstallMode>none</osInstallMode>
        <hostId>{{ host_id }}</hostId>
        <hostPoolId>{{ hp_id }}</hostPoolId>
        <formatEnable>1</formatEnable>
        <imgFileType></imgFileType>
        <network>
            <vsId>{{ vs_id }}</vsId>
            <vsName>{{ vs_name }}</vsName>
            <deviceModel>virtio</deviceModel>
            <profileId>{{ profile_id }}</profileId>
            <isKernelAccelerated>1</isKernelAccelerated>
            <mac>{{ mac_addr }}</mac>
        </network>
        <storage>
            <storeFile>{{ store_file }}</storeFile>
            <targetBus>virtio</targetBus>
            <cacheType>writeback</cacheType>
            <assignType>1</assignType>
            <type>file</type>
            <driveType>qcow2</driveType>
            <device>disk</device>
        </storage>
    </domain>''')
    for i in xrange(1, 5):
        try:
            r = request('post', '/cas/casrs/vm/add', data=t.render(c))
            task_info = r.json()
            # {u'msgId': u'1448420536259', u'completed': u'false', u'eventType': u'0', u'progress': u'0'}
            task_info = wait_for_task(task_info['msgId'], timeout=30)
            # {
            #   u'name': u'\u589e\u52a0\u865a\u62df\u673a\u201cc45_stu_50\u201d\u3002',
            #   u'failMsg': u'',
            #   u'msgId': u'1448420536254',
            #   u'completed': u'true',
            #   u'targetId': u'12953',
            #   u'detail': u'\u589e\u52a0\u865a\u62df\u673a\u201cc45_stu_50\u201d\u6210\u529f\u3002',
            #   u'start': u'2015-11-25T14:09:14.699+08:00',
            #   u'result': u'0',
            #   u'eventType': u'20',
            #   u'progress': u'100',
            #   u'targetName': u'c45_stu_50',
            #   u'refreshData': [
            #     {u'value': u'1', u'key': u'3'},
            #     {u'value': u'12953', u'key': u'5'}
            #   ],
            #   u'complete': u'2015-11-25T14:09:17.545+08:00'
            # }
            if task_info['result'] == u'0':  # 0:成功 1:失败 2:部分成功
                return task_info['targetId']
        except VmAlreadyExist:
            vm_info = get_vms_by_name(host_id, vm_name)
            if vm_info:
                return vm_info['id']
        except:
            LOG.exception('Failed to create vm %s, %d times' % (vm_name, i))
        time.sleep(i * i)


def create_vm(hostid, hpid, name, desc, mem, cpu_count, cpu_cores, system_type, os_version,
              img_filename, vs_id, vs_name, npp_id, storage_path, os_install_mode):
    """创建VM"""
    c = Context({
        'name': name,
        'title': name,
        'description': desc,
        'memory': mem,
        'memory_priority': '50',  # 内存资源优先级。枚举值：0=低，50=中，100=高
        'cpu_sockets': cpu_count,  # cpu个数
        'cpu_cores': cpu_cores,  # cpu核数
        'cpu_shares': '1024',  # CPU调度优先级，枚举值：1024：高，512：中，256：低。
        'max_cpu_socket': '5',  # 主机允许的最大CPU核数
        'blkiotune': '500',  # I/O优先级，枚举值：500：高，300：中，200：低。
        'system': system_type,  # 操作系统类型，枚举值：0：Windows,1：Linux。
        'os_version': os_version,
        'auto_migrate': '0',  # 是否允许虚拟机自动迁移，实现资源动态调整，枚举值：1=允许，0=不允许。
        'priority': '2',  # 启动优先级，当集群启用HA后有效，枚举值：0：低级，1：中级，2：高级。
        'os_install_mode': os_install_mode,  # 虚拟机操作系统安装方式
        'img_filename': img_filename,  # /vm's/isos/winxp.iso
        'host_id': hostid,  # 1
        'hostpool_id': hpid,  # 2
        'format_enable': '1',
        'network_vs_id': vs_id,  # 虚拟交换机id。
        'network_vs_name': vs_name,  # 虚拟交换机名称。vswitch0
        'network_device_model': 'virtio',  # 网卡设备型号
        'network_profile_id': npp_id,  # 网络策略模板id
        'network_is_kernel_accelerated': '1',  # 是否设置内核加速
        'storage_store_file': storage_path,  # /vms/ssd/stu_1
        'storage_target_bus': 'virtio',  # 存储设备类型
        'storage_cache_type': 'directsync',  # 磁盘缓存方式
        'storage_assign_type': '1',  # 分配类型: 0 指定 1 动态分配。
        'storage_type': 'file',  # 类型。如 file block
        'storage_drive_type': 'qcow2'
        # 存储卷类型，必须和使用的存储卷的类型保持一致，枚举值：qcow2，raw
    })

    t = Template(u'''
    <domain>
        <name>{{ name }}</name>
        <title>{{ title }}</title>
        <description>{{ description }}</description>
        <memory>{{ memory }}</memory>
        <memoryPriority>{{ memory_priority }}</memoryPriority>
        <cpuSockets>{{ cpu_sockets }}</cpuSockets>
        <cpuCores>{{ cpu_cores }}</cpuCores>
        <cpuShares>{{ cpu_shares }}</cpuShares>
        <maxCpuSocket>{{ max_cpu_socket }}</maxCpuSocket>
        <blkiotune>{{ blkiotune }}</blkiotune>
        <system>{{ system }}</system>
        <osVersion>{{ os_version }}</osVersion>
        <autoMigrate>{{ auto_migrate }}</autoMigrate>
        <priority>{{ priority }}</priority>
        <osInstallMode>{{ os_install_mode }}</osInstallMode>
        <imgFileName>{{ img_filename }}</imgFileName>
        <hostId>{{ host_id }}</hostId>
        <hostPoolId>{{ hostpool_id }}</hostPoolId>
        <formatEnable>{{ format_enable }}</formatEnable>
        <imgFileType></imgFileType>
        <autoLoadVirtio>true</autoLoadVirtio>
        <network>
            <vsId>{{ network_vs_id }}</vsId>
            <vsName>{{ network_vs_name }}</vsName>
            <deviceModel>{{ network_device_model }}</deviceModel>
            <profileId>{{ network_profile_id }}</profileId>
            <isKernelAccelerated>{{ network_is_kernel_accelerated }}</isKernelAccelerated>
        </network>
        <storage>
            <storeFile>{{ storage_store_file }}</storeFile>
            <targetBus>{{ storage_target_bus }}</targetBus>
            <cacheType>{{ storage_cache_type }}</cacheType>
            <assignType>{{ storage_assign_type }}</assignType>
            <type>{{ storage_type }}</type>
            <driveType>{{ storage_drive_type}}</driveType>
        </storage>
    </domain>''')
    r = request('post', '/cas/casrs/vm/add', data=t.render(c))
    return r.json()


def start_vm(vmid, wait=False):
    """启动虚拟机。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.start_vm(1416)
      {u'completed': u'false',
       u'eventType': u'0',
       u'msgId': u'1440745875877',
       u'progress': u'0',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

      >>> casapi.start_vm(1416, True)
      {u'complete': u'2015-09-18T12:49:03.829+08:00',
       u'completed': u'true',
       u'detail': u'\u542f\u52a8\u865a\u62df\u673a\u201cwins7.base\u201d\u6210\u529f\u3002',
       u'eventType': u'30',
       u'failMsg': u'',
       u'msgId': u'1442551446492',
       u'name': u'\u542f\u52a8\u865a\u62df\u673a\u201cwins7.base\u201d\u3002',
       u'progress': u'100',
       u'refreshData': {u'key': u'5', u'value': u'1416'},
       u'result': u'0',
       u'start': u'2015-09-18T12:49:03.035+08:00',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}
      {u'name': u'\u542f\u52a8\u865a\u62df\u673a\u201cc45_stu_12\u201d\u3002',
       u'failMsg': u'\u4e3b\u673a\u5f02\u5e38\u6216\u8005\u6b63\u5728\u5904\u7406\u5176\u5b83\u4e8b\u52a1\uff0c\u8bf7\u7a0d\u5019\u91cd\u8bd5\u3002',
       u'msgId': u'1448526736419',
       u'completed': u'true',
       u'targetId': u'14573',
       u'detail': u'\u542f\u52a8\u865a\u62df\u673a\u201cc45_stu_12\u201d\u5931\u8d25\u3002\u539f\u56e0\uff1a\u4e3b\u673a\u5f02\u5e38\u6216\u8005\u6b63\u5728\u5904\u7406\u5176\u5b83\u4e8b\u52a1\uff0c\u8bf7\u7a0d\u5019\u91cd\u8bd5\u3002',
       u'start': u'2015-11-26T16:44:45.858+08:00',
       u'result': u'1',
       u'eventType': u'30',
       u'progress': u'100',
       u'targetName': u'c45_stu_12',
       u'refreshData': {u'value': u'14573', u'key': u'5'},
       u'complete': u'2015-11-26T16:44:46.040+08:00'}

    """
    r = request('put', '/cas/casrs/vm/start/%s' % vmid)
    task_info = r.json()
    if wait:
        task_id = task_info[u'msgId']
        task_info = wait_for_task(task_id)
    return task_info


def restart_vm(vmid, wait=False):
    """重新启动虚拟机。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.restart_vm(1416)
      {u'completed': u'false',
       u'eventType': u'0',
       u'msgId': u'1442551446499',
       u'progress': u'0',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

      >>> casapi.restart_vm(1416, True)
      {u'complete': u'2015-09-18T13:45:18.117+08:00',
       u'completed': u'true',
       u'detail': u'\u91cd\u542f\u865a\u62df\u673a\u201cwins7.base\u201d\u6210\u529f\u3002',
       u'eventType': u'33',
       u'failMsg'      : u'',
       u'msgId': u'1442551446500',
       u'name': u'\u91cd\u542f\u865a\u62df\u673a\u201cwins7.base\u201d\u3002',
       u'progress': u'100',
       u'refreshData': {u'key': u'5', u'value': u'1416'},
       u'result': u'0',
       u'start': u'2015-09-18T13:44:51.179+08:00',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

    """
    r = request('put', '/cas/casrs/vm/restart/%s' % vmid)
    task_info = r.json()
    if wait:
        task_id = task_info[u'msgId']
        task_info = wait_for_task(task_id)
    return task_info


def pause_vm(vmid, wait=False):
    """暂停虚拟机。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.pause_vm(1416)
      {u'completed': u'false',
       u'eventType': u'0',
       u'msgId': u'1442551446498',
       u'progress': u'0',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

      >>> casapi.pause_vm(1416, True)
      {u'complete': u'2015-09-18T13:41:30.289+08:00',
       u'completed': u'true',
       u'detail': u'\u6682\u505c\u865a\u62df\u673a\u201cwins7.base\u201d\u6210\u529f\u3002',
       u'eventType': u'34',
       u'failMsg': u'',
       u'msgId': u'1442551446496',
       u'name': u'\u6682\u505c\u865a\u62df\u673a\u201cwins7.base\u201d\u3002',
       u'progress': u'100',
       u'refreshData': {u'key': u'5', u'value': u'1416'},
       u'result': u'0',
       u'start': u'2015-09-18T13:41:30.200+08:00',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

    """
    r = request('put', '/cas/casrs/vm/pause/%s' % vmid)
    task_info = r.json()
    if wait:
        task_id = task_info[u'msgId']
        task_info = wait_for_task(task_id)
    return task_info


def stop_vm(vmid, wait=False):
    """关闭虚拟机。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.stop_vm(1416)
      {u'completed': u'false',
       u'eventType': u'0',
       u'msgId': u'1442551446491',
       u'progress': u'0',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

      >>> casapi.stop_vm(1416, True)
      {u'complete': u'2015-09-18T12:49:56.210+08:00',
       u'completed': u'true',
       u'detail': u'\u5173\u95ed\u865a\u62df\u673a\u201cwins7.base\u201d\u6210\u529f\u3002',
       u'eventType': u'32',
       u'failMsg': u'',
       u'msgId': u'1442551446493',
       u'name': u'\u5173\u95ed\u865a\u62df\u673a\u201cwins7.base\u201d\u3002',
       u'progress': u'100',
       u'refreshData': {u'key': u'5', u'value': u'1416'},
       u'result': u'0',
       u'start': u'2015-09-18T12:49:56.118+08:00',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

    """
    r = request('put', '/cas/casrs/vm/stop/%s' % vmid)
    task_info = r.json()
    if wait:
        task_id = task_info[u'msgId']
        task_info = wait_for_task(task_id)
    return task_info


def power_off_vm(vmid, wait=False):
    """强制关闭虚拟机

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.power_off_vm(1416)
      {u'completed': u'false',
       u'eventType': u'0',
       u'msgId': u'1442551446501',
       u'progress': u'0',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

       >>> casapi.power_off_vm(1416, True)
       {u'complete': u'2015-09-18T13:49:27.074+08:00',
        u'completed': u'true',
        u'detail': u'\u5173\u95ed\u865a\u62df\u673a\u201cwins7.base\u201d\u7535\u6e90\u6210\u529f\u3002',
        u'eventType': u'31',
        u'failMsg': u'',
        u'msgId': u'1442551446503',
        u'name': u'\u5173\u95ed\u865a\u62df\u673a\u201cwins7.base\u201d\u7535\u6e90\u3002',
        u'progress': u'100',
        u'refreshData': {u'key': u'5', u'value': u'1416'},
        u'result': u'0',
        u'start': u'2015-09-18T13:49:26.559+08:00',
        u'targetId': u'1416',
        u'targetName': u'wins7.base'}

    """
    r = request('put', '/cas/casrs/vm/powerOff/%s' % vmid)
    task_info = r.json()
    if wait:
        task_id = task_info[u'msgId']
        task_info = wait_for_task(task_id)
    return task_info


def delete_vm(vmid, wait=False):
    """删除虚拟机。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.delete_vm(1416)
      {u'completed': u'false',
       u'eventType': u'0',
       u'msgId': u'1442551446504',
       u'progress': u'0',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

      >>> casapi.delete_vm(1416, True)
      {u'complete': u'2015-09-18T14:42:31.297+08:00',
       u'completed': u'true',
       u'detail': u'\u5220\u9664\u865a\u62df\u673a\u201cwins7.base\u201d\u6210\u529f\u3002',
       u'eventType': u'21',
       u'failMsg': u'',
       u'msgId': u'1442551446505',
       u'name': u'\u5220\u9664\u865a\u62df\u673a\u201cwins7.base\u201d\u3002',
       u'progress': u'100',
       u'refreshData': {u'key': u'3', u'value': u'6'},
       u'result': u'0',
       u'start': u'2015-09-18T14:42:31.104+08:00',
       u'targetId': u'1416',
       u'targetName': u'wins7.base'}

    """
    r = request('delete', '/cas/casrs/vm/delete/%s' % vmid)
    task_info = r.json()
    if wait:
        task_id = task_info['msgId']
        task_info = wait_for_task(task_id)
    return task_info


def delete_vm_with_volume(vmid):
    # type: 0 - keep disks, 1 - delete disks
    r = request('delete', '/cas/casrs/vm/deleteVm?id=%s&type=1' % vmid)
    return r.json()


def add_devicetovm(id, name, path, cachetype='none', type='virtio', devicetype='disk'):
    url = '/cas/casrs/vm/addDevice'
    t = Template(u'''
    <domain>
      <id>{{ id }}</id>
      <name>{{ name }}</name>
      <storage>
        <device>{{ devicetype }}</device>
        <targetBus>{{ type }}</targetBus>
        <path>{{ path }}</path>
        <cacheType>{{ cachetype }}</cacheType>
      </storage>
    </domain>''')
    c = Context({
        'id': id,
        'name': name,
        'type': type,  # ide, scsi, usb, virtio, cdrom, floppy
        'path': path,
        'devicetype': devicetype,
        'cachetype': cachetype,  # directsync，writethrough，writeback，none
    })
    r = request('put', url, data=t.render(c))
    return r


def add_castools(vmid, name):
    c = Context({
        'id': id,
        'name': name
    })
    t = Template(u'''
    <domain>
      <id>{{ id }}</id>
      <name>{{ name }}</name>
      <storage>
        <device>cdrom</device>
      <type>ide</type>
      <path>/vms/isos/castools.iso</path>
      <format>raw</format>
        <targetBus>ide</targetBus>
        <cacheType>directsync</cacheType>
      </storage>
    </domain>''')
    r = request('put', '/cas/casrs/vm/addDevice', data=t.render(c))
    return r


def add_cdrom(vmid, name, isopath):
    c = Context({
        'id': vmid,
        'name': name,
        'isopath': isopath,
    })
    t = Template(u'''
    <domain>
      <id>{{ id }}</id>
      <name>{{ name }}</name>
      <storage>
        <device>cdrom</device>
      <type>ide</type>
      <path>{{ isopath }}</path>
      <format>raw</format>
        <targetBus>ide</targetBus>
        <cacheType>directsync</cacheType>
      </storage>
    </domain>''')
    r = request('put', '/cas/casrs/vm/addDevice', data=t.render(c))
    return r


def del_devicefromvm(id, name, devicename):
    """卸载虚拟硬盘"""
    c = Context({
        'id': id,
        'name': name,
        'devicename': devicename
    })
    t = Template(u'''
    <domain>
      <id>{{ id }}</id>
      <name>{{ name }}</name>
      <storage>
        <deviceName>{{ devicename }}</deviceName>
      </storage>
    </domain>''')
    request('put', '/cas/casrs/vm/delDevice', data=t.render(c))


def get_vnc_info(vmid):
    """获取VNC信息。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_vnc_info(1416)
      {u'ip': u'10.88.16.98', u'port': u'-1'}

    """
    r = request('get', '/cas/casrs/vmvnc/vnc/%s' % vmid)
    return r.json()


def create_volume(hostid, storage_pool, name, capacity):
    """添加存储卷"""
    c = Context({
        'hostId': hostid,
        'spName': storage_pool,
        'volName': name,
        'capacity': capacity,
        'format': "qcow2"
    })
    t = Template(u'''
    <volAddParameter>
      <hostId>{{ hostId }}</hostId>
      <spName>{{ spName }}</spName>
      <volName>{{ volName }}</volName>
      <capacity>{{ capacity }}</capacity>
      <format>{{ format }}</format>
    </volAddParameter>''')
    request('post', '/cas/casrs/storage/volume/add', data=t.render(c))
    storage_pool_path = settings.DEFAULT_STORAGE_POOL.get(storage_pool)
    storage_file_path = os.path.join(storage_pool_path, name)
    return storage_file_path


def preload_image(src_img, preload_dir):
    options = [src_img, preload_dir]
    cp(options)


def clone_vm(hostid, src_vm_id, src_vm_name, dst_vm_name, storage_pool, clone_mode=1):
    """快速克隆虚拟机"""
    c = Context({
        'hostid': hostid,
        'storage_pool': storage_pool,
        'src_vm_id': src_vm_id,
        'src_vm_name': src_vm_name,
        'dst_vm_name': dst_vm_name,
        'clone_mode': clone_mode,
    })
    t = Template(u'''
    <vmCloneParameter>
      <id>{{ src_vm_id }}</id>
      <targetHostId>{{ hostid }}</targetHostId>
      <domainName>{{ dst_vm_name }}</domainName>
      <title>{{ dst_vm_name }}</title>
      <cloneMode>{{clone_mode}}</cloneMode>
      <cloneType>0</cloneType>
      <diskFormat>qcow2</diskFormat>
      <storage>
        <src>{{ src_vm_name }}</src>
        <dest>{{ dst_vm_name }}</dest>
        <pool>{{ storage_pool }}</pool>
      </storage>
    </vmCloneParameter>''')
    r = request('put', '/cas/casrs/vm/clone', data=t.render(c))
    return r.json()


def reboot_host(hostid):
    """重启主机。"""
    shutdown(['-r', 'now'])


def shutoff_host(hostid):
    """关闭主机。"""
    shutdown(['-h', 'now'])


def get_acls(**kwargs):
    """获取ACL列表。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_acls()
      [{u'@id': u'1',
        u'createTime': u'2015-08-14T11:20:43+08:00',
        u'defaultAclAction': u'1',
        u'defaultAclOutAction': u'0',
        u'name': u'defaultacl',
        u'rule': {u'@id': u'34',
                  u'action': u'1',
                  u'direction': u'1',
                  u'priority': u'1',
                  u'protocol': u'65535',
                  u'srcIp': u'10.88.16.0',
                  u'srcMask': u'255.255.254.0'},
        u'timeRangeEnabled': u'0',
        u'type': u'3'}]

    """
    r = request('get', '/cas/casrs/acl', **kwargs)
    acls = r.json()['aclStrategy']
    if not isinstance(acls, list):
        acls = [acls]
    return acls


def get_acl_info(aclid, **kwargs):
    r = request('get', '/cas/casrs/acl/%s' % aclid, **kwargs)
    return r.json()


def create_vswitch(name, description, hostid, port_num, pnic, enable_lacp, address, netmask, gateway):
    """ 创建虚拟交换机vswitch """
    t = Template(
        u"""
        <vSwitch>
            <name>{{ name }}</name>
            <hostId>{{ hostid }}</hostId>
            <portNum>{{ port_num }}</portNum>
            <mode>0</mode>
            <pnic>{{ pnic }}</pnic>
            <status>1</status>
            <address>{{ address }}</address>
            <netmask>{{ netmask }}</netmask>
            <gateway>{{ gateway }}</gateway>
            <enableLacp>{{ enable_lacp }}</enableLacp>
            <description>{{ description }}</description>
        </vSwitch>
        """
    )
    c = Context({
        'name': name,
        'description': description,
        'hostid': hostid,
        'port_num': port_num,
        'pnic': ','.join(pnic),
        'address': address,
        'netmask': netmask,
        'enable_lacp': enable_lacp,
        'gateway': gateway
    })
    r = request('post', '/cas/casrs/vswitch', data=t.render(c))
    return r


def create_profile(name, description, vlan_id=None):
    """ 创建网络策略模板 """
    t = Template(
        u"""
        <portProfile>
            <name>{{ name }}</name>
            <description>{{ description }}</description>
            {% if vlan_id %}<vlanId>{{ vlan_id }}</vlanId>{% endif %}
        </portProfile>
        """
    )
    c = Context({
        'name': name,
        'description': description,
        'vlan_id': vlan_id,
    })
    r = request('post', '/cas/casrs/profile', data=t.render(c))
    return r


def create_acl(name, description='', default_acl_action=1, default_acl_out_action=1, type=3, time_range_enabled=0):
    """ 创建ACL策略 """
    t = Template(
        u"""
        <aclStrategy>
          <name>{{ name }}</name>
          <description>{{ description }}</description>
          <defaultAclAction>{{ default_acl_action }}</defaultAclAction>
          <defaultAclOutAction>{{ default_acl_out_action }} </defaultAclOutAction>
          <type>{{ type }}</type>
          <timeRangeEnabled>0</timeRangeEnabled>
        </aclStrategy>
        """
    )
    c = Context({
        'name': name,
        'description': description,
        'default_acl_action': default_acl_action,
        'default_acl_out_action': default_acl_out_action,
        'type': type,
        'time_range_enabled': time_range_enabled
    })
    r = request('post', '/cas/casrs/acl', data=t.render(c))
    return r


def add_acl_to_profile(d, acl_strategy_id, acl_name, **kwargs):
    """
    网络策略模板添加 ACL
    """
    if 'data' not in kwargs:
        c = Context({
            'd': d,
            'acl_strategy_id': acl_strategy_id,
            'acl_name': acl_name
        })
        t = Template(u'''
        <portProfile>
            {% for k, v in d.items %}
            <{{ k }}>{{ v }}</{{ k }}>
            {% endfor %}
            <aclStrategyId>{{ acl_strategy_id }} </aclStrategyId>
            <aclName>{{ acl_name }}</aclName>
        </portProfile>
        ''')
        kwargs['data'] = t.render(c)
    r = request('put', '/cas/casrs/profile', **kwargs)
    return r


def set_acl_rules(aclid, aclname, in_action, out_action, rules=None):
    """设置 ACL 规则

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.set_acl_rules(1, 'defaultacl', 1, 1)

    """
    if rules is None:
        rules = []

    c = Context({
        'aclid': aclid,
        'aclname': aclname,
        'in_action': in_action,
        'out_action': out_action,
        'rules': rules,
    })
    t = Template(u'''
    <aclStrategy id="{{ aclid }}">
      <name>{{ aclname }}</name>
      <defaultAclAction>{{ in_action }}</defaultAclAction>
      <defaultAclOutAction>{{ out_action }}</defaultAclOutAction>
      {% for rule in rules %}
      <rule>
        <protocol>65535</protocol>
        <srcIp>{{ rule.src_addr }}</srcIp>
        <srcMask>{{ rule.src_mask }}</srcMask>
        <action>{{ rule.action }}</action>
        <direction>1</direction>
      </rule>
      {% endfor %}
      <type>3</type>
      <timeRangeEnabled>0</timeRangeEnabled>
    </aclStrategy>''')
    request('put', '/cas/casrs/acl', data=t.render(c))


def get_pnics(hostid, **kwargs):
    """获取指定主机可用物理网卡列表。

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.get_pnics(6)
      [u'eth2', u'eth3']

    """
    r = request('get', '/cas/casrs/host/pnic?id=%s' % hostid, **kwargs)

    if r.json():
        traffic_info = r.json()[u'trafficInfo']
        if not isinstance(traffic_info, list):
            traffic_info = [traffic_info]

        pnics = [x[u'vPortName'] for x in traffic_info]
        return pnics


def refresh_storagepool(hostid, poolname):
    """刷新存储池"""
    url = "/cas/casrs/storage/refresh?id={}&poolName={}".format(hostid, poolname)
    request('get', url)


def add_castools(vmid, name, path, devicename):
    """连接光驱"""
    c = Context({
        'id': vmid,
        'name': name,
        'path': path,
        'devicename': devicename,
    })
    t = Template(u'''
    <domain>
      <id>{{ id }}</id>
      <name>{{ name }}</name>
      <cdrom>
        <device>{{ devicename }}</device>
        <operation>connect</operation>
        <path>{{ path }}</path>
        <type>tool</type>
      </cdrom>
    </domain>''')
    r = request('put', '/cas/casrs/vm/modify', data=t.render(c))
    return r.json()


def test_conn():
    """测试连通性

    Usage::

      >>> from cloudapi.casapi import casapi
      >>> casapi.test_conn()
      True
    """
    r = request('get', '/cas/casrs/operator/test')
    return r.status_code == 204
