# -*- coding: utf-8 -*-
from contextlib import contextmanager
import datetime
import glob
import hashlib
import json
import logging
import os
import struct
import tarfile
import tempfile
import time
import zipfile

from django.utils import six

from h3cloudclass.activation.hostinfo import Customer, Nic, HostInfo, export_hostinfo
# noinspection PyUnresolvedReferences
from h3cloudclass.activation.license import import_license, validate_license, generate_trail, get_trail_days

from utils.vendor.filesize import naturalsize

LOG = logging.getLogger(__name__)


def get_isos(dirpath):
    dirpath = os.path.abspath(dirpath)
    isos = []
    for i in glob.glob('%s/*.[Ii][Ss][Oo]' % dirpath):
        if os.path.isfile(i):
            fstat = os.stat(i)
            LOG.debug(i)
            iso = {
                'name': os.path.basename(i),
                'path': i,
                'size': naturalsize(fstat.st_size),
                'ctime': datetime.datetime.fromtimestamp(
                    os.path.getctime(i)).strftime('%Y-%m-%d %H:%M:%S'),
                'mtime': time.ctime(fstat.st_mtime)
            }

            isos.append(iso)
    return isos


def get_softs(dirpath):
    dirpath = os.path.abspath(dirpath)
    isos = []
    for i in glob.glob('%s/*.*' % dirpath):
        if os.path.isfile(i):
            fstat = os.stat(i)
            LOG.debug(i)
            iso = {
                'name': os.path.basename(i),
                'path': i,
                'size': naturalsize(fstat.st_size),
                'ctime': datetime.datetime.fromtimestamp(
                    os.path.getctime(i)).strftime('%Y-%m-%d %H:%M:%S'),
                'mtime': time.ctime(fstat.st_mtime)
            }
            isos.append(iso)
    return isos


def del_iso(dirpath, isofile):
    dirpath = os.path.abspath(dirpath)
    fpath = os.path.join(dirpath, isofile)
    if isinstance(fpath, unicode):
        fpath = fpath.encode('utf-8')
    os.unlink(fpath)


def get_upgrades(path, parent="#"):
    current_files = os.listdir(path)
    all_files = []

    for file_name in current_files:
        full_file_name = os.path.join(path, file_name)
        fstat = os.stat(full_file_name)
        iso = {
            'id': full_file_name,
            'parent': parent,
            'text': os.path.basename(full_file_name),
            'icon': 'glyphicon glyphicon-leaf'
        }

        if os.path.isdir(full_file_name):
            dirlist = full_file_name.split("/")
            dir = dirlist[len(dirlist)-1]
            diriso = {"id": full_file_name, "parent": parent, "text": dir}
            all_files.append(diriso)
            next_level_files = get_upgrades(full_file_name, full_file_name)
            all_files.extend(next_level_files)
        else:
            all_files.append(iso)
    return all_files


def get_recursive_file_list(path):
    current_files = os.listdir(path)
    all_files = []
    for file_name in current_files:
        full_file_name = os.path.join(path, file_name)

        fstat = os.stat(full_file_name)
        iso = {
            'name': os.path.basename(full_file_name),
            'path': full_file_name,
            'size': fstat.st_size,
            'ctime':  datetime.datetime.fromtimestamp(fstat.st_ctime).strftime('%Y-%m-%d%H:%M:%S') ,
            'mtime':  datetime.datetime.fromtimestamp(fstat.st_mtime).strftime('%Y-%m-%d%H:%M:%S') ,
        }
        if os.path.isdir(full_file_name):
            next_level_files = get_recursive_file_list(full_file_name)
            all_files.extend(next_level_files)
        else:
            all_files.append(iso)

    return all_files


def write_to_file(content, filename):
    if isinstance(filename, unicode):
        filename = filename.encode('utf-8')
    if isinstance(content, unicode):
        content = content.encode('utf-8')

    with open(filename, 'w') as f:
        f.write(content)


def get_base_images(dirpath):
    dirpath = os.path.abspath(dirpath)
    images = []
    for fpath in glob.glob('%s/*.base' % dirpath):
        size = 0
        if os.path.isfile(fpath):
            with open(fpath, 'rb') as f:
                f.seek(0)
                if f.read(4) == 'QFI\xfb':  # qcow2 format
                    f.seek(24)
                    size = struct.unpack('>Q', f.read(8))[0] / 1024 / 1024  # big endian, bytes
        if size > 0:
            images.append({
                'name': os.path.basename(fpath),
                'path': fpath,
                'size': size,  # in bytes
                'md5': 'd41d8cd98f00b204e9800998ecf8427e',  # FIXME using fake md5sum instead of md5sum(fpath)
            })
    return images


def get_course_pkgfiles(dirpath):
    files = []
    dirpath = os.path.abspath(dirpath)
    for fpath in glob.glob('%s/*.ipkg' % dirpath):
        if os.path.isfile(fpath):
            files.append({
                'name': os.path.basename(fpath),
                'path': fpath,
            })
    return files


def check_course_pkgfile(pkgfile):
    if not os.path.join(pkgfile):
        return u'找不到课程导入包。请刷新后重试！'

    if isinstance(pkgfile, unicode):
        pkgfile = pkgfile.encode('utf-8')

    try:
        tarf = tarfile.open(pkgfile)
        names = tarf.getnames()
        tarf.close()
        if 'metadata.json' not in names:
            return u'不是有效的课程导入包。请确认课程导入包完整性！'
    except tarfile.TarError:
        return u'不是有效的课程导入包。请确认课程导入包完整性！'


def extract_metadata_json(pkgfile):
    """
    {
        "base_file": "基础镜像文件名称",
        "base_name": "基础镜像名称",
        "base_md5": "基础镜像校验哈希",
        "course_file": "课程镜像文件名称",
        "course_name": "课程镜像名称",
        "course_md5": "课程镜像校验哈希",
        "os_type": "操作系统类型",
        "os_version": "操作系统版本"
    }
    """
    if isinstance(pkgfile, unicode):
        pkgfile = pkgfile.encode('utf-8')

    with tarfile.open(pkgfile, 'r') as tarf:
        content = tarf.extractfile('metadata.json').read()
    return json.loads(content)


def extract_image(dirpath, pkgfile, image_file):
    if isinstance(pkgfile, unicode):
        pkgfile = pkgfile.encode('utf-8')
    if isinstance(image_file, unicode):
        image_file = image_file.encode('utf-8')

    with tarfile.open(pkgfile, 'r') as tarf:
        tarf.extract(image_file, dirpath)


def get_last_partial(content, ps=4194304, bs=4096):
    """Get the last partial of the file-like object

    :param content: file-like object
    :param ps: partial size, unit is bytes, default is 4MiB
    :return: the special sized partial of content, default is 4KiB
    """
    def reversed_blocks(fobj, ps, bs):
        fobj.seek(0, os.SEEK_END)
        fsize = fobj.tell()
        cpos = fsize
        total = min(ps, fsize)
        sz = 0
        while sz < total:
            delta = min(bs, cpos)
            cpos -= delta
            fobj.seek(cpos, os.SEEK_SET)
            sz += delta
            yield fobj.read(delta)

    return ''.join(list(reversed(list(reversed_blocks(content, ps, bs)))))


def collect_logs():
    """Update `filelist` to collect more logs

    :return: file-like object with zipped content
    """
    def recursion(zfile, path):
        for x in glob.glob('%s/*' % path):
            if os.path.isfile(x):
                zf.writestr(get_arcname(x), get_last_partial(open(x, 'rb')))
            if os.path.isdir(x):
                recursion(zfile, x)

    def get_arcname(filepath):
        arcname = os.path.normpath(os.path.splitdrive(filepath)[1])
        while arcname[0] in (os.sep, os.altsep):
            arcname = arcname[1:]
        return arcname

    filelist = ['/opt/classskyline/.revfile',
                '/var/log/nginx',
                '/opt/classskyline/log/classskyline.log',
                '/var/log/upstart/h3class-uwsgi.log',
                '/var/log/upstart/h3class-dnsmasq.log',
                '/var/log/h3client.log',
                '/var/log/operation',
                '/var/log/libvirt',
                '/var/log/tomcat6/cas.log',
                '/var/lib/casserver/logs',
                '/var/log/openvswitch']

    logfile = six.StringIO()
    # file structure tree
    with zipfile.ZipFile(logfile, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i in filelist:
            if os.path.isfile(i):
                zf.writestr(get_arcname(i), get_last_partial(open(i, 'rb')))
            elif os.path.isdir(i):
                recursion(zf, i)
    logfile.seek(0)
    return logfile


def generate_host_info(name, country, province, company, email, phone, macs):
    customer = Customer(name, country, province, company, email, phone)
    nics = [Nic(mac) for mac in macs]
    hostinfo = HostInfo(int(time.time()), customer, nics)
    return export_hostinfo(hostinfo.to_string())


def get_content(stream, filename, raw_data):
    BUFFER_SIZE = 8192  # 8K
    content = six.StringIO()
    """:type : StringIO.StringIO"""
    try:
        if raw_data:
            # File was uploaded via ajax, and is streaming in.
            chunk = stream.read(BUFFER_SIZE)
            while len(chunk) > 0:
                content.write(chunk)
                chunk = stream.read(BUFFER_SIZE)
        else:
            # File was uploaded via a POST, and is here.
            for chunk in stream.chunks():
                content.write(chunk)
        return content.getvalue()
    except:
        # things went badly.
        pass


def md5sum(path):
    if isinstance(path, unicode):
        path = path.encode('utf-8')

    md5 = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5.update(chunk)
    return md5.hexdigest()


@contextmanager
def atomic_write(destf):
    dirname, basename = os.path.split(destf)
    tmpf = tempfile.mktemp(prefix=basename, dir=dirname)
    try:
        with open(tmpf, 'w') as f:
            yield f
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmpf, destf)
    finally:
        # double check
        if os.path.isfile(tmpf):
            try:
                os.unlink(tmpf)
            except (IOError, OSError):
                pass
