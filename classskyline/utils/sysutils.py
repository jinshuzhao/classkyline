# -*- coding: utf-8 -*-
import os
import re

try:
    from utils.vendor import sh
except ImportError:
    pass

ERRNO_NO_HPSA = 1
ERRNO_NO_CMD = 2
ERRNO_NOT_EXECUTE_PROPERLY = 3


def check_hpsa_state():
    if not os.path.exists('/sys/bus/pci/drivers/hpsa'):
        return ERRNO_NO_HPSA

    try:
        hpssacli = sh.Command('/usr/sbin/hpssacli')
    except sh.CommandNotFound:
        return ERRNO_NO_CMD

    try:
        output = hpssacli('controller', 'all', 'show', 'status')
    except sh.ErrorReturnCode:
        return ERRNO_NOT_EXECUTE_PROPERLY

    controller_status = output.stdout

    slots = re.findall(r'Slot (\w)', output.stdout)
    for slot in slots:
        try:
            output = hpssacli('controller', 'slot={slot}'.format(slot=slot),
                              'logicaldrive', 'all', 'show')
        except sh.ErrorReturnCode:
            return ERRNO_NOT_EXECUTE_PROPERLY
        print('=== Logical Drives ===')
        logicaldrives = re.findall(r'(logicaldrive [0-9]+) \(([0-9.]+ [A-Z]+), (RAID [0-9+]+), ([a-zA-Z]+)\)', output.stdout)
        print(logicaldrives)

        try:
            output = hpssacli('controller', 'slot={slot}'.format(slot=slot), 'physicaldrive', 'all', 'show')
        except sh.ErrorReturnCode:
            return ERRNO_NOT_EXECUTE_PROPERLY
        print('=== Physical Drives ===')
        physicaldrives = re.findall(r'(physicaldrive \S+) \(.*, (\S+), ([0-9.]+ [A-Z]+), ([a-zA-Z]+)\)', output.stdout)
        print(physicaldrives)
        # C:Failed C:Disabled
        # C:Failed W:Failure W:Rebuild W:Recover W:'Cache Status: Temporarily Disabled' W:FIRMWARE


def get_nic_macs():
    try:
        ip = sh.Command('/sbin/ip')
    except sh.CommandNotFound:
        return ERRNO_NO_CMD

    try:
        output = ip('link', 'show')
    except sh.ErrorReturnCode:
        return ERRNO_NOT_EXECUTE_PROPERLY
    mac_list = re.findall(r'link/ether ([0-9a-zA-Z:-]+)', output.stdout)

    return mac_list


def get_dminfo():
    serial_list = []
    try:
        dmidecode = sh.Command('/usr/sbin/dmidecode')
    except sh.CommandNotFound:
        return ERRNO_NO_CMD

    try:
        output = dmidecode('-s', 'system-serial-number')
    except sh.ErrorReturnCode:
        return ERRNO_NOT_EXECUTE_PROPERLY
    serial_list.append({'system': output.stdout})

    try:
        output = dmidecode('-s', 'chassis-serial-number')
    except sh.ErrorReturnCode:
        return ERRNO_NOT_EXECUTE_PROPERLY
    serial_list.append({'chassis': output.stdout})

    return serial_list


def restart_services():
    """重启后台服务"""
    try:
        service = sh.Command('/usr/sbin/service')
    except sh.CommandNotFound:
        return ERRNO_NO_CMD

    try:
        service('libvirt-bin', 'stop')
    except sh.ErrorReturnCode:
        pass
    try:
        service('libvirt-bin', 'start')
    except sh.ErrorReturnCode:
        pass
