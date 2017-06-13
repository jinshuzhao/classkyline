# -*- coding: utf-8 -*-
import logging
import os
import string
import re

import time

from utils.vendor.IPy import IP
try:
    from utils.vendor.sh import ErrorReturnCode, rm, kill, ip, ovs_vsctl, touch, initctl, mkdir
except ImportError:
    pass

LOG = logging.getLogger(__name__)


H3CLASS_DHCP_NAMESPACE = 'h3class-dhcp-namespace'
H3CLASS_DHCP_INTERFACE = 'hccdhcp0'
CONF_DIR = '/etc/dnsmasq'
LOG_DIR = '/var/log/dnsmasq'
VLAN_RANGE = (1, 4094)


def fmt_time(seconds):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(seconds))


class Dnsmasq(object):

    def __init__(self, vswitch_name, vlan_tag):
        self._vswitch_name = vswitch_name
        self._vlan_tag = vlan_tag
        self._prepare_dirs()

    def _prepare_dirs(self):
        mkdir('-p', CONF_DIR)
        mkdir('-p', LOG_DIR)

    @property
    def pidfile(self):
        return os.path.join(CONF_DIR, '{}.dnsmasq.pid'.format(H3CLASS_DHCP_INTERFACE))

    @property
    def optsfile(self):
        return os.path.join(CONF_DIR, '{}.optsfile'.format(H3CLASS_DHCP_INTERFACE))

    @property
    def hostfile(self):
        return os.path.join(CONF_DIR, '{}.hostsfile'.format(H3CLASS_DHCP_INTERFACE))

    @property
    def addnhosts(self):
        return os.path.join(CONF_DIR, '{}.addnhosts'.format(H3CLASS_DHCP_INTERFACE))

    @property
    def leasefile(self):
        return os.path.join(CONF_DIR, '{}.leases'.format(H3CLASS_DHCP_INTERFACE))

    @property
    def logfile(self):
        return os.path.join(LOG_DIR, '{}.log'.format(H3CLASS_DHCP_INTERFACE))

    @property
    def descfile(self):
        return os.path.join(CONF_DIR, '{}.dnsmasq.desc'.format(H3CLASS_DHCP_INTERFACE))

    @property
    def conffile(self):
        return os.path.join(CONF_DIR, '{}.dnsmasq.conf'.format(H3CLASS_DHCP_INTERFACE))

    def get_pid(self):
        with open(self.pidfile, 'r') as f:
            pid = f.read().rstrip('\n')
        return pid

    def define(self, address_begin, address_end, netmask, gateway, dns, fixed_pairs, lease_time):
        lease_max = 253  # to prevent DoS attacks, default is 1000

        self._check_dhcp_range_validity(address_begin, address_end, netmask)

        self._check_vlan_validity(self._vlan_tag)
        self.add_port()
        with open(self.descfile, 'w') as f:
            f.write('interface={},{},{}'.format(H3CLASS_DHCP_INTERFACE, address_begin, netmask))

        self._check_mac_validity(*fixed_pairs.keys())
        self._check_ipv4_validity(*fixed_pairs.values())
        with open(self.hostfile, 'w') as f:
            for hwaddr, ipaddr in fixed_pairs.items():
                f.write('{},{}\n'.format(hwaddr, ipaddr))

        with open(self.optsfile, 'w') as f:
            contents = [
                'option:router,{}\n'.format(gateway or ''),
                'option:dns-server,{}\n'.format(dns or ''),
            ]
            for line in contents:
                f.write(line)

        touch(self.addnhosts)
        touch(self.leasefile)
        touch(self.pidfile)
        touch(self.logfile)

        with open(self.conffile, 'w') as f:
            contents = [
                'strict-order\n',
                'user=libvirt-dnsmasq\n',
                'except-interface=lo\n',
                'bind-interfaces\n',
                'interface={}\n'.format(H3CLASS_DHCP_INTERFACE),
                'dhcp-range={},{},{},{}\n'.format(address_begin, address_end, netmask, lease_time),
                'dhcp-lease-max={}\n'.format(lease_max),
                'pid-file={}\n'.format(self.pidfile),
                'dhcp-optsfile={}\n'.format(self.optsfile),
                'dhcp-hostsfile={}\n'.format(self.hostfile),
                'dhcp-leasefile={}\n'.format(self.leasefile),
                'addn-hosts={}\n'.format(self.addnhosts),
                'log-facility={}\n'.format(self.logfile),
            ]
            for line in contents:
                f.write(line)

    def clear_leasefile(self):
        with open(self.leasefile, 'w'):
            pass

    def modify(self):
        raise NotImplementedError()

    def destroy(self):
        self.del_port()
        self.cleanup()

    def cleanup(self):
        if os.path.isfile(self.pidfile):
            rm('-f', self.pidfile)
        if os.path.isfile(self.optsfile):
            rm('-f', self.optsfile)
        if os.path.isfile(self.hostfile):
            rm('-f', self.hostfile)
        if os.path.isfile(self.leasefile):
            rm('-f', self.leasefile)
        if os.path.isfile(self.logfile):
            rm('-f', self.logfile)
        self.del_port()
        if os.path.isfile(self.descfile):
            rm('-f', self.descfile)
        if os.path.isfile(self.conffile):
            rm('-f', self.conffile)

    @staticmethod
    def start_service():
        try:
            out = initctl('start', 'h3class-dnsmasq')
            return 'start/running' in out
        except ErrorReturnCode:
            return False

    @staticmethod
    def stop_service():
        try:
            out = initctl('stop', 'h3class-dnsmasq')
            return 'stop/waiting' in out
        except ErrorReturnCode:
            return False

    @staticmethod
    def is_running():
        try:
            out = initctl('status', 'h3class-dnsmasq')
            return 'start/running' in out
        except ErrorReturnCode:
            return False

    @staticmethod
    def exec_ns(*args):
        ip('netns', 'exec', H3CLASS_DHCP_NAMESPACE, *args)

    def add_port(self):
        ovs_vsctl('-t', '5', '--', '--may-exist', 'add-port', self._vswitch_name, H3CLASS_DHCP_INTERFACE,
                  '--', 'set', 'Interface', H3CLASS_DHCP_INTERFACE, 'type=internal')
        if self._vlan_tag == 1:
            ovs_vsctl('-t', '5', 'clear', 'port', H3CLASS_DHCP_INTERFACE, 'tag')
        else:
            ovs_vsctl('-t', '5', 'set', 'port', H3CLASS_DHCP_INTERFACE, 'tag=%d' % self._vlan_tag)
        # ip('link', 'set', H3CLASS_DHCP_INTERFACE, 'netns', H3CLASS_DHCP_NAMESPACE)
        # self.exec_ns('ifconfig', H3CLASS_DHCP_INTERFACE, ipaddr, 'netmask', mask)

    def del_port(self):
        ovs_vsctl('-t', '5', '--', '--if-exists', 'del-port', self._vswitch_name, H3CLASS_DHCP_INTERFACE)

    @staticmethod
    def get_value(filename, *args):
        result = {}
        with open(filename, 'r') as f:
            entries = f.readlines()
        for key in args:
            for entry in entries:
                if entry.startswith('{}='.format(key)):
                    result[key] = entry.split('=', 1)[1]
                    break
        return result

    @staticmethod
    def set_value(filename, **kwargs):
        with open(filename, 'r') as f:
            entries = f.readlines()
        with open(filename, 'w') as f:
            for entry in entries:
                for key in kwargs.keys():
                    if entry.startswith('{}='.format(key)):
                        f.write('{}={}\n'.format(key, kwargs[key]))
                        del kwargs[key]
                        break
            for key in kwargs.keys():
                f.write('{}={}\n'.format(key, kwargs[key]))

    def add_fixed_ipaddr(self, hwaddr, ipaddr):
        self._check_mac_validity(hwaddr)
        self._check_ipv4_validity(ipaddr)
        with open(self.hostfile, 'a') as f:
            f.write('{},{}\n'.format(hwaddr, ipaddr))
        kill('-hup', self.get_pid())

    def del_fixed_ipaddr(self, hwaddr):
        self._check_mac_validity(hwaddr)
        with open(self.hostfile, 'r') as f:
            entries = f.readlines()
        for entry in iter(entries):
            _hwaddr = entry.split(',')[0]
            if hwaddr == _hwaddr:
                entries.remove(entry)
        kill('-hup', self.get_pid())

    def list_leases(self):
        dhcp_range = self.get_value(self.conffile, 'dhcp-range')['dhcp-range'].strip().split(',')
        lease_time = dhcp_range[3]
        leases = []
        with open(self.leasefile, 'r') as f:
            for entry in f.readlines():
                info = entry.rstrip('\n').split()
                if lease_time == 'infinite':
                    begin_time = end_time = 'infinite'
                else:
                    begin_time = fmt_time(string.atoi(info[:-1]))
                    end_time = fmt_time(string.atoi(info[0]))
                hwaddr = info[1]
                ipaddr = info[2]
                hostname = info[3]
                leases.append({
                    'begin_time': begin_time,
                    'end_time': end_time,
                    'hwaddr': hwaddr,
                    'ipaddr': ipaddr,
                    'hostname': hostname})
        return leases

    @staticmethod
    def _check_ipv4_validity(*args):
        pattern = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')
        for ipaddr in args:
            if not pattern.match(ipaddr):
                raise Exception('IP address {} is invalid'.format(ipaddr))

    @staticmethod
    def _check_mac_validity(*args):
        pattern = re.compile(r'^([a-fA-F0-9]{2}:){5}([a-fA-F0-9]{2})$')
        for hwaddr in args:
            if not pattern.match(hwaddr):
                raise Exception('Mac address {} is invalid'.format(hwaddr))

    @staticmethod
    def _check_vlan_validity(vlan):
        if vlan is None or vlan < VLAN_RANGE[0] or vlan > VLAN_RANGE[1]:
            raise Exception('VLAN ID {} is invalid'.format(vlan))

    @staticmethod
    def _check_dhcp_range_validity(address_begin, address_end, netmask):
        ipaddr1 = IP(address_begin)
        ipaddr2 = IP(address_end)
        if ipaddr1 > ipaddr2:
            raise Exception('The begin address MUST be smaller than the end address')

        segment1 = ipaddr1.make_net(netmask)
        segment2 = ipaddr2.make_net(netmask)
        if segment1 != segment2:
            raise Exception('The begin address and end address MUST be in same network segment')


def config_dhcp_service(vswitch_name, vlan_tag, address_begin, address_end, netmask, gateway, dns, pairs, lease_time):
    dnsmasq = Dnsmasq(vswitch_name, vlan_tag)
    dnsmasq.define(address_begin, address_end, netmask, gateway, dns, pairs, lease_time)
    Dnsmasq.stop_service()
    dnsmasq.clear_leasefile()
    Dnsmasq.start_service()
