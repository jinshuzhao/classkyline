# -*- coding: utf-8 -*-
from __future__ import division

from datetime import datetime
import glob
import inspect
import logging
import os
import re
import time
from django.db import IntegrityError
from requests import HTTPError

from django.conf import settings
from django.utils import six
from cloudapi.casapi.exceptions import VmDoesNotExist

from cloudapi.driver import VirtDriver
from cloudapi.casapi import casapi

from common.models import Host, Desktop, DesktopImage, Classroom
from utils import netutils
from utils import cacheutils
from utils import dbutils
from utils import settingsutils
from utils.netutils import MAC_TYPE_VM
from utils.settingsutils import OptsMgr, VSWITCH_NAME, NPP_NAME, ACL_NAME, ACL_WHITELIST, VSWITCH_ID
from utils.threadhelper import ThreadPool, WorkRequest
from utils.vendor.retrying import retry
from utils.vendor.IPy import IP
try:
    from utils.vendor.sh import rm, virsh, sed, ErrorReturnCode
except ImportError:
    pass

LOG = logging.getLogger(__name__)
BEGIN_COURSE_THREAD_POOL = ThreadPool(settings.DEFAULT_THREAD_COUNT)
MISC_THREAD_POOL = ThreadPool(settings.DEFAULT_THREAD_COUNT)
DELETE_THREAD_POOL = ThreadPool(5)
FREE_COURSE_THREAD_POOL = ThreadPool(settings.DEFAULT_THREAD_COUNT)
DESKTOP_NAME_PATTERN = re.compile(r'c[0-9]+_{}_[0-9]+'.format(settings.DEFAULT_DESKTOP_PREFIX))


def retry_on_http_error(exception):
    return isinstance(exception, HTTPError)


def retry_on_error_code(exception):
    LOG.exception('Failed to start instance!')
    return isinstance(exception, ErrorReturnCode)


def retry_if_result_none(result):
    return result is None


class CasDriver(VirtDriver):
    def __init__(self):
        super(CasDriver, self).__init__()
        self._initialize_db()

    def _initialize_db(self):
        # update host
        host = Host.objects.last()
        try:
            hostid = casapi.get_host()[u'id']
            info = casapi.get_host_info(hostid)
            if not info:
                raise Exception('Cannot get host info from CAS!')
        except:
            LOG.error('Failed to initialize database!')
            return

        if host:
            if host.uuid != info[u'id']:
                host.uuid = info[u'id']
                host.save()
        else:
            host = Host.objects.create(
                uuid=info[u'id'],
                ip_address=info[u'ip'],
                cpu=info[u'cpuCount'],
                memory=info[u'memorySize'],
                disk=info[u'diskSize'],
                virt_type=Host.VIRT_CAS
            )
        try:
            classroom = Classroom.objects.get(name='default')
            if classroom.host != host:
                classroom.host = host
                classroom.save(update_fields=['host'])
        except Classroom.DoesNotExist:
            Classroom.objects.create(
                name='default',
                seats=75,
                host=host)

    def revert_desktop(self, host, desktop):
        # FIXME remove when use new get_visitor API
        desktop.clean_protocol1()
        desktop.clean_protocol2()
        cacheutils.clear_desktop(desktop)

        while True:
            task_info = casapi.power_off_vm(desktop.uuid)
            if task_info is not None:
                casapi.wait_for_task(task_info['msgId'])
                break

        course = desktop.course
        vm_name = self.generate_vmname(course.id, desktop.name)
        storage_pool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()
        if settings.DESKTOP_USING_TMPFS:
            dst_img = os.path.join(settings.PRELOAD_IMAGE_DIR, vm_name)
        else:
            dst_img = os.path.join(storage_pool, vm_name)
        casapi.create_backing_volume(course.image.image_path, dst_img)

        wreq = WorkRequest(self._wait_for_desktop, args=(host.uuid, desktop, host.ip_address))
        FREE_COURSE_THREAD_POOL.putRequest(wreq)

    def delete_desktops_ex(self, host, wait=True):
        # 销毁CAS中残留的虚拟机
        for vm in self.get_desktops(host):
            req = WorkRequest(self.__delete_vm, args=(vm['id'], True))
            DELETE_THREAD_POOL.putRequest(req)
        if wait:
            DELETE_THREAD_POOL.wait()

    def poweroff_desktops(self, desktops):
        # 批量关闭虚拟机
        for desktop in desktops:
            casapi.power_off_vm(desktop.uuid)
            desktop.clean_protocol1()
            desktop.clean_protocol2()
            desktop.save()
            cacheutils.clear_desktop(desktop)

    def delete_desktops(self, desktops, wait=True):
        # 批量删除虚拟机
        for desktop in desktops:
            req = WorkRequest(self.del_vm_thread, args=[desktop])
            DELETE_THREAD_POOL.putRequest(req)
        if wait:
            DELETE_THREAD_POOL.wait()

    def del_vm_thread(self, desktop):
        dbutils.thread_started.send(sender=inspect.stack()[0][3])
        try:
            self.__delete_vm(desktop.uuid)
        except:
            LOG.exception('Failed to delete vm {}'.format(desktop.name))

        desktop.clean_protocol1()
        desktop.clean_protocol2()
        image = desktop.image
        if os.path.exists(image.image_path):
            try:
                rm('-f', image.image_path)
            except:
                pass
        try:
            desktop.delete()
        except IntegrityError:
            LOG.exception('Failed to delete desktop {}'.format(desktop.name))
        try:
            image.delete()
        except IntegrityError:
            LOG.exception('Failed to delete image {}'.format(image.image_path))
        cacheutils.clear_desktop(desktop)

    def generate_hostname(self, prefix_name, index):
        """生成有序的虚拟机主机名"""
        return prefix_name + '_%02d' % int(index)

    def generate_vmname(self, course_id, hostname):
        """生成虚拟机名称，课程ID作为前缀，防止多个课程之间的名称冲突"""
        return 'c%d_%s' % (course_id, hostname)

    def _get_store_files(self, vmid):
        vm_info = casapi.get_vm_info(vmid)
        return vm_info['storage']

    # wait_fixed: 1000ms = 1s
    @retry(retry_on_exception=retry_on_http_error,
           stop_max_attempt_number=5,
           wait_fixed=1000)
    def __delete_vm(self, vmid, close_db=False):
        if close_db:
            dbutils.thread_started.send(sender=inspect.stack()[0][3])
        if vmid:
            casapi.delete_vm(vmid, True)

    def free_course(self, host, course, network, terminal_number_id, hostname):
        # 销毁CAS中残留的虚拟机
        for vm in casapi.get_vms_by_name_suffix(host.uuid, hostname):
            self.__delete_vm(vm['id'])

        vm_name = VirtDriver.instance().generate_vmname(course.id, hostname)
        storage_pool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()

        dst_img = os.path.join(storage_pool, vm_name)
        casapi.create_backing_volume(course.image.image_path, dst_img)
        image = DesktopImage.objects.update_or_create(defaults={
            'parent': course.image,
            'name': vm_name,
            'capacity': 20480,
            'image_path': dst_img}, name=vm_name)[0]

        hpid = casapi.get_hostpool()[u'id']
        vsid = OptsMgr.get_value(VSWITCH_ID)
        vsname = OptsMgr.get_value(VSWITCH_NAME)

        npp_info = casapi.get_npp_info(OptsMgr.get_value(NPP_NAME))

        mac = netutils.random_mac(0x00, MAC_TYPE_VM, terminal_number_id)
        # todo 修改配置
        cpu = course.profile.cpu
        mem = course.profile.memory

        vmid = casapi.create_vm_hack(hpid, host.uuid, course.get_os_version_display(), vsid, vsname,
                                     npp_info['id'], vm_name, dst_img, mac, cpu, mem)
        if not vmid:
            return
        desktop = Desktop.objects.create(
            name=hostname,
            uuid=str(vmid),
            mac_address=mac,
            ip_address=self.get_ip_from_pool(network, terminal_number_id),
            protocol2=Desktop.PROTO_VNC,  # NB: 兼容老接口
            course=course,
            image=image)
        wreq = WorkRequest(self._wait_for_desktop, args=(host.uuid, desktop, host.ip_address))
        FREE_COURSE_THREAD_POOL.putRequest(wreq)
        return True

    def _wait_for_desktop(self, host_id, desktop, hostaddr):
        dbutils.thread_started.send(sender=inspect.stack()[0][3])
        self.get_desktop_vm_id(host_id, desktop, hostaddr)
        self._wait_rdp_for_desktop(desktop)

    def preload_course_image(self, course_name, storage_pool):
        preload_dir = settings.PRELOAD_IMAGE_DIR
        src_vm_image = os.path.join(storage_pool, course_name)
        preload_image = os.path.join(preload_dir, course_name)
        # 删除其他临时课程镜像
        for fp in glob.glob('%s/*.course' % preload_dir):
            if not fp.endswith(course_name):
                rm('-f', fp)
        if os.path.exists(preload_image):
            s_stat = os.stat(src_vm_image)
            d_stat = os.stat(preload_image)
            s_size = s_stat.st_size
            d_size = d_stat.st_size
            s_mtime = int(s_stat.st_mtime)
            d_mtime = int(d_stat.st_mtime)
            if s_size == d_size and s_mtime == d_mtime:  # 如果大小一致，不再复制
                return
        # 复制当前课程镜像
        casapi.preload_image(src_vm_image, preload_dir)

    @staticmethod
    def clean_store_files(storage_pool):
        try:
            for f in os.listdir(storage_pool):
                if DESKTOP_NAME_PATTERN.match(f):
                    try:
                        rm('-f', os.path.join(storage_pool, f))
                    except:
                        pass
        except:
            LOG.exception('Failed to clean store files!')

    def begin_course(self, host, course, network, prefix_name, count):
        # 销毁所有已创建的虚拟机
        desktops = Desktop.objects.all()
        self.delete_desktops(desktops, False)
        self.delete_desktops_ex(host, False)
        DELETE_THREAD_POOL.wait()

        if settings.DESKTOP_USING_TMPFS:
            storage_pool = settings.PRELOAD_IMAGE_DIR
        else:
            storage_pool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()
        self.clean_store_files(storage_pool)
        if settings.COURSE_USING_TMPFS:
            src_pool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()
            self.preload_course_image(course.name, src_pool)  # 预先载入模板镜像

        hpid = casapi.get_hostpool()[u'id']
        vsid = OptsMgr.get_value(VSWITCH_ID)
        vsname = OptsMgr.get_value(VSWITCH_NAME)

        npp_info = casapi.get_npp_info(OptsMgr.get_value(NPP_NAME))
        npp_id = npp_info[u'id']
        self.begin_course_normal(course, network, prefix_name, count, storage_pool, hpid, host.uuid,
                                 host.ip_address, vsid, vsname, npp_id)

    def begin_course_normal(self, course, network, prefix_name, count,
                            storage_pool, hp_id, host_id, host_addr, vs_id, vs_name, profile_id):
        def add_desktop_to_list_cb(request, result):
            if result:
                wreq = WorkRequest(self._wait_rdp_for_desktop, args=(result, True))
                MISC_THREAD_POOL.putRequest(wreq)

        cpu = course.profile.cpu
        mem = course.profile.memory
        # TODO 检查当前硬件配置，根据硬件配置决定数量
        if cpu == 2 and count * 2 > settingsutils.get_max_users():
            count //= 2

        for i in xrange(1, count + 1):
            wreq = WorkRequest(self.create_desktop_thread,
                               args=(course, network, prefix_name, i,
                                     storage_pool, hp_id, host_id, host_addr, vs_id, vs_name, profile_id, cpu, mem),
                               callback=add_desktop_to_list_cb)
            BEGIN_COURSE_THREAD_POOL.putRequest(wreq)

        # blocking request until all work requests are done.
        BEGIN_COURSE_THREAD_POOL.wait()

    def create_desktop_thread(self, course, network, prefix_name, index,
                              storage_pool, hp_id, host_id, host_addr, vs_id, vs_name, profile_id, cpu, mem):
        dbutils.thread_started.send(sender=inspect.stack()[0][3])
        hostname = self.generate_hostname(prefix_name, index)
        vm_name = self.generate_vmname(course.id, hostname)

        if settings.COURSE_USING_TMPFS:
            src_img = os.path.join(settings.PRELOAD_IMAGE_DIR, course.name)
        else:
            src_img = course.image.image_path
        dst_img = os.path.join(storage_pool, vm_name)
        casapi.create_backing_volume(src_img, dst_img)
        image = DesktopImage.objects.update_or_create(defaults={
            'parent': course.image,
            'name': vm_name,
            'capacity': 20480,
            'image_path': dst_img}, name=vm_name)[0]

        mac = netutils.random_mac(0x00, MAC_TYPE_VM, index)
        vmid = casapi.create_vm_hack(hp_id, host_id, course.get_os_version_display(), vs_id, vs_name,
                                     profile_id, vm_name, dst_img, mac, cpu, mem)
        if not vmid:
            return

        desktop = Desktop.objects.create(
            name=hostname,
            uuid=str(vmid),
            mac_address=mac,
            ip_address=self.get_ip_from_pool(network, index),
            protocol2=Desktop.PROTO_VNC,  # NB: 兼容老接口
            course=course,
            image=image)
        self.get_desktop_vm_id(host_id, desktop, host_addr)
        return desktop

    def get_courses(self, host_id):
        vms = casapi.get_all_vms_of_host(host_id)

        # TODO 设置操作系统 LOGO
        # courses = [{'name': x['name'], 'desc': '','id': x['id']}
        # for x in vms if x['name'].endswith('.base')]

        if not isinstance(vms, list):
            vms = [vms]
        courses = [{'name': x['name'], 'desc': '', 'id': x['id']}
                   for x in vms if x['name'].endswith('.course')]
        return courses

    def get_desktops(self, host):
        vms = casapi.get_all_vms_of_host(host.uuid)

        desktops = [{'name': x['name'], 'macaddr': '00.00.00.00',
                     'ipaddr': '0.0.0.0', 'id': x['id']}
                    for x in vms
                    if DESKTOP_NAME_PATTERN.match(x['name'])]
        return desktops

    def get_all_vms(self, host_id):
        vms = casapi.get_all_vms_of_host(host_id)

        dic = {"vm_all": len(vms)}

        count = 0
        for x in vms:
            if x["vmStatus"] == "running":
                count += 1
        dic["vm_run"] = count
        return dic

    def add_course(self, hpid, hostid, name, image_path, desc, cpu_cnt, cpu_cores, mem,
                   os_type, os_version, img_filename, vsid, vsname, nppid, os_install_mode):
        try:
            msg = casapi.create_vm(hostid, hpid, name, desc, mem, cpu_cnt, cpu_cores,
                                   os_type, os_version, img_filename, vsid, vsname, nppid,
                                   image_path, os_install_mode)
            return msg
        except:
            LOG.exception('Failed to create vm %s' % name)

    def get_vm_id(self, msg_id, course):
        """等待虚拟机创建任务完成，虚拟机上电"""
        try:
            LOG.debug('Msg_id = %s' % msg_id)
            task_info = casapi.wait_for_task(msg_id)
            vm_id = task_info["targetId"]
            LOG.debug('vm_id = %s' % vm_id)
            if course is not None:
                course.uuid = vm_id
                course.save()
                cacheutils.clear_course(course)
        except:
            LOG.exception('Failed to get vm %s id' % course.name)

    def get_base_image_vm_id(self, msg_id):
        """ base镜像创建虚机 """
        task_info = casapi.wait_for_task(msg_id)
        vm_id = task_info['targetId']
        return vm_id

    def get_ip_from_pool(self, network, index):
        ip_address = ''
        if network is not None:
            address_begin = IP(network.address_begin)
            address_end = IP(network.address_end)

            # ip_address_begin is used by DHCP interface, start with ip_address_begin + 1
            ip = IP(address_begin.int() + index + 1)
            if ip > address_end:
                LOG.warning('no more ip address')
            else:
                ip_address = ip.strNormal()
        return ip_address

    # stop_max_attempt_number: 10times
    # wait_exponential_multiplier: 1000ms = 1s
    # wait_exponential_max: 20000ms = 20s
    @retry(retry_on_exception=retry_on_error_code,
           stop_max_attempt_number=10,
           wait_exponential_multiplier=1000,
           wait_exponential_max=20000)
    def __virsh_start_vm(self, vmname):
        virsh('start', vmname)

    # stop_max_attempt_number: 10times
    # wait_exponential_multiplier: 1000ms = 1s
    # wait_exponential_max: 20000ms = 20s
    @retry(retry_on_result=retry_if_result_none,
           stop_max_attempt_number=10,
           wait_exponential_multiplier=1000,
           wait_exponential_max=20000)
    def __start_vm1(self, vmname, vmid):
        try:
            task_info = casapi.start_vm(vmid, True)
            if task_info['result'] == u'0':
                return 'success'
        except:
            LOG.exception('====__start_vm1 {}'.format(vmname))

    def get_desktop_vm_id(self, host_id, desktop, hostaddr):
        vm_name = self.generate_vmname(desktop.course.id, desktop.name)
        try:
            # self.__virsh_start_vm(vm_name)
            self.__start_vm1(vm_name, desktop.uuid)
            self._wait_vnc_for_desktop(desktop, hostaddr)
        except:
            LOG.exception('failed to get desktop uuid')

    def attach_share_image(self, vm_id, vm_name):
        self.power_off_vm(vm_id)

        store_files = self._get_store_files(vm_id)
        # 卸载光驱，软驱
        for store in store_files:
            if store['diskDevice'] == u'\u5149\u9a71' or \
                    store['diskDevice'] == u'\u8f6f\u76d8' or str(store['storeFile']) == \
                    settings.DEFAULT_SHARE_IMAGE['defaultvolume']:
                dev_name = store['device']
                casapi.del_devicefromvm(vm_id, vm_name, dev_name)
        # 添加共享硬盘
        result = casapi.add_devicetovm(vm_id, vm_name, settings.DEFAULT_SHARE_IMAGE['defaultvolume'])
        domain_xml = os.path.join('/etc/libvirt/qemu', '{}.xml'.format(vm_name))
        try:
            # FIXME: There has no choice but to support readonly disk in cas by this way
            sed('-i', r'/\/vms\/isos\/share.img/a\      <readonly\/>\n      <shareable\/>', domain_xml)
            virsh('define', domain_xml)
        except ErrorReturnCode:
            LOG.exception('Failed to set readonly and shareable.')
        return result

    def remove_sharedisk(self, course):
        vm_id = course.uuid
        vm_name = course.name

        store_files = self._get_store_files(vm_id)
        # 卸载光驱，软驱
        for store in store_files:
            if str(store['storeFile']) == settings.DEFAULT_SHARE_IMAGE['defaultvolume']:
                dev_name = store['device']
                casapi.del_devicefromvm(vm_id, vm_name, dev_name)

    def delete_course(self, course):
        if course.uuid:
            try:
                casapi.delete_vm(course.uuid)
            except VmDoesNotExist:
                LOG.info('vm[{}] not found'.format(course.uuid))
        image = course.image
        if os.path.isfile(image.image_path):
            try:
                rm('-f', image.image_path)
            except:
                pass
        try:
            image.delete()
        except IntegrityError:
            LOG.exception('Failed to delete {}'.format(course))
        cacheutils.clear_course(course)

    def get_host_monitor(self, host_uuid):
        return casapi.get_host_monitor(host_uuid)

    def get_host_summary(self, host_uuid):
        return casapi.get_host_summary(host_uuid)

    def power_on_vm(self, vm_uuid):
        summary = casapi.get_vm_summary(vm_uuid)
        status = summary.get(u'\u72b6\u6001') or summary.get(u'Status')
        if status != 'running':
            return casapi.start_vm(vm_uuid)

    # stop_max_attempt_number: 4times
    # wait_exponential_multiplier: 1000ms = 1s
    @retry(stop_max_attempt_number=4,
           wait_exponential_multiplier=1000)
    def __poweron_vm(self, vmid):
        task_info = casapi.start_vm(vmid)
        return task_info['msgId']

    def poweron(self, host, desktop):
        taskid = self.__poweron_vm(desktop.uuid)

        # FIXME remove when use new get_visitor API
        desktop.clean_protocol1()
        desktop.clean_protocol2()
        cacheutils.clear_desktop(desktop)

        wreq = WorkRequest(self._wait_for_desktop2, args=(desktop, taskid, host))
        FREE_COURSE_THREAD_POOL.putRequest(wreq)

    def _wait_vnc_for_desktop(self, desktop, hostaddr, reset=True):
        if reset:
            desktop.clean_protocol1()
            desktop.clean_protocol2()
            cacheutils.clear_desktop(desktop)
        # 获取VNC port
        time_started = datetime.now()
        while True:
            time_passed = datetime.now() - time_started
            if time_passed.total_seconds() > 20:
                break

            try:
                vncinfo = casapi.get_vnc_info(desktop.uuid)
                if int(vncinfo['port']) != -1:
                    try:
                        desktop.set_protocol2(hostaddr, int(vncinfo['port']))
                        cacheutils.clear_desktop(desktop)
                    except:
                        LOG.exception('_wait_vnc_for_desktop')
                    LOG.debug("Get end vnc info, desktop = %s" % desktop)
                    break
            except:
                LOG.exception('Failed to get vnc info for %s[%s]' % (
                    desktop.name, desktop.uuid))
            time.sleep(1)  # sleep 1 seconds for next loop

    def _wait_rdp_for_desktop(self, desktop, close_db=False):
        if close_db:
            dbutils.thread_started.send(sender=inspect.stack()[0][3])
        seconds_started = time.time()
        while True:
            seconds_passed = time.time() - seconds_started
            if seconds_passed > 20:
                LOG.error('Failed to get CAS Tools status!')
                break

            try:
                ipaddrs = casapi.get_vm_ipaddrs(desktop.uuid)
                if desktop.ip_address in ipaddrs:
                    break
                # summary = casapi.get_vm_summary(desktop.uuid)
                # if summary[u'CAS Tools'] == u'\u8fd0\u884c':
                #     break
            except:
                pass
            time.sleep(1)  # sleep 1 seconds for next loop
        try:
            desktop.set_protocol1(desktop.ip_address)
            cacheutils.clear_desktop(desktop)
        except:
            LOG.exception(u'Failed to set protocol1 for desktop {}'.format(desktop.name))

    def _wait_for_desktop2(self, desktop, taskid, hostaddr):
        dbutils.thread_started.send(sender=inspect.stack()[0][3])
        casapi.wait_for_task(taskid)
        self._wait_vnc_for_desktop(desktop, hostaddr, reset=False)
        self._wait_rdp_for_desktop(desktop)

    # stop_max_attempt_number: 4times
    # wait_exponential_multiplier: 1000ms = 1s
    @retry(stop_max_attempt_number=4,
           wait_exponential_multiplier=1000)
    def __restart_vm(self, vmid):
        task_info = casapi.restart_vm(vmid)
        return task_info['msgId']

    def reboot(self, host, desktop):
        # host 是业务口 IP 地址
        taskid = self.__restart_vm(desktop.uuid)

        # FIXME remove when use new get_visitor API
        desktop.clean_protocol1()
        desktop.clean_protocol2()
        cacheutils.clear_desktop(desktop)

        wreq = WorkRequest(self._wait_for_desktop2, args=(desktop, taskid, host))
        FREE_COURSE_THREAD_POOL.putRequest(wreq)

    def power_off_vm(self, vm_uuid):
        summary = casapi.get_vm_summary(vm_uuid)
        status = summary.get(u'\u72b6\u6001') or summary.get(u'Status')
        if status != 'shutOff':
            return casapi.stop_vm(vm_uuid)

    def force_power_off_vm(self, vm_uuid, wait=False):
        summary = casapi.get_vm_summary(vm_uuid)
        status = summary.get(u'\u72b6\u6001') or summary.get(u'Status')
        if status != 'shutOff':
            taskinfo = casapi.power_off_vm(vm_uuid)
            if wait:
                return casapi.wait_for_task(taskinfo['msgId'])
            else:
                return taskinfo

    def get_vm_status(self, vm_id):
        summary = casapi.get_vm_summary(vm_id)
        return summary.get(u'\u72b6\u6001') or summary.get(u'Status')

    def shut_vm_and_remove_disk(self, vm_id, vm_name):
        self.power_off_vm(vm_id)
        while True:
            status = self.get_vm_status(vm_id)
            if status == "shutOff":
                break

        store_files = self._get_store_files(vm_id)
        # 卸载光驱，软驱
        for store in store_files:
            if store['diskDevice'] == u'\u5149\u9a71' or \
                    store['diskDevice'] == u'\u8f6f\u76d8' or str(store['storeFile']) == \
                    settings.DEFAULT_SHARE_IMAGE["defaultvolume"]:
                dev_name = store['device']
                casapi.del_devicefromvm(vm_id, vm_name, dev_name)

    def shutdown_vm(self, vm_id):
        # 关闭虚拟机
        task = self.power_off_vm(vm_id)
        if task:
            casapi.wait_for_task(task['msgId'], 2)

    def reboot_host(self, host_id):
        casapi.reboot_host(host_id)

    def shutoff_host(self, host_id):
        casapi.shutoff_host(host_id)

    def set_activate_external_network(self, action):
        acl_name = OptsMgr.get_value(ACL_NAME)
        for acl in casapi.get_acls():
            if acl['name'] == acl_name:
                acl_id = acl['@id']
                break
        else:
            return

        if action == 'OPEN':
            casapi.set_acl_rules(acl_id, acl_name, 1, 1)
        else:
            rules = []
            for cidr in OptsMgr.get_value(ACL_WHITELIST).split(','):
                segment = IP(cidr)
                d = {
                    'src_addr': segment.strNormal(0),
                    'src_mask': segment.strNetmask(),
                    'action': 1,
                }
                rules.append(d)

            casapi.set_acl_rules(acl_id, acl_name, 1, 0, rules)

    def install_castools(self, vm_id, vm_name, path, type):
        # TODO 检查对应的盘符是否安装cdrom

        if type:
            r = casapi.add_castools(vm_id, vm_name)
            return r.status_code == 204
        store_files = self._get_store_files(vm_id)
        # 卸载光驱，软驱
        hascdrom = False
        devicename = 'hdd'
        for store in store_files:
            if store['diskDevice'] == u'\u8f6f\u76d8':
                devicename = store['device']
                hascdrom = True
                r = casapi.add_castools(vm_id, vm_name, path, devicename)
                return r.status_code == 204

        if not hascdrom:
            # 添加共享硬盘
            r = casapi.add_castools(vm_id, vm_name)
            return r.status_code == 204
