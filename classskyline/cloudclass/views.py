# -*- coding: utf-8 -*-
from __future__ import division

import base64
import os
import re
import logging
import struct
import uuid
import csv
from django.views.decorators.csrf import csrf_exempt

import requests
from requests.auth import HTTPDigestAuth

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.servers.basehttp import FileWrapper
from django.utils import six
from django.template import Context, Template
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from cloudapi.driver import VirtDriver
from cloudapi.casapi.driver import CasDriver
from cloudapi.casapi import casapi
from common.models import BaseImage, Course, Desktop, Terminal, Network, Host, CourseProfile, CourseImage, Classroom, BaseImageExtras, Student, Gradeclass
from utils import cacheutils
from utils import dhcputils
from utils import fileutils
from utils import settingsutils
from utils import courseutils
from utils.vendor.IPy import IP
from utils.commonutility import form_error_msg
from utils.httputils import JsonResponseBadRequest, HttpResponseNoContent
from utils.netutils import random_mac, MAC_TYPE_VM
from utils.settingsutils import OptsMgr, CAS_ADDRESS, CAS_USERNAME, CAS_PASSWORD, CAS_HOSTPOOL, \
    SSH_ADDRESS, SSH_USERNAME, SSH_PASSWORD, VSWITCH_ID, VSWITCH_NAME, NPP_ID, NPP_NAME, VLAN_TAG, \
    ACL_ID, ACL_NAME, ACL_WHITELIST, INITIALIZED, ACTIVATION_LICENSE, DESKTOP_COUNT
try:
    from utils.vendor.sh import rm, cp
except ImportError:
    pass


from cloudclass.forms import BaseImageForm, CourseImageForm, AddBaseInfoForm, TeacherForm, TeacherEditForm, PasswordChangeForm, \
    EditBaseImageNameForm,GradeForm, GradeEditForm, StudentForm, StudentEditForm, ChangeStudentPassword
import json

LOG = logging.getLogger(__name__)


@login_required
@require_GET
def dash_board(request):
    return render(request, 'cloudclass/dashboard.html')


@login_required
@require_GET
def images(request):
    """基础镜像"""
    base_images = BaseImage.objects.all()

    base_images = [{'name': image.name, 'id': image.id, 'img_url': image.get_os_img_url(), 'refname': image.refname,
                    'vm_id': image.extras.vm_id if image.extras else '', 'image_path': image.image_path,
                    'os_version': image.os_version, 'capacity': image.capacity, 'published': image.published}
                   for image in base_images]
    form = BaseImageForm()
    ctx = {
        'base_images': base_images,
        'isoftp': settingsutils.get_ftp_url(request, 'isos'),
        'imagesftp': settingsutils.get_ftp_url(request, 'images'),
        'form': form,
        'base_info_form': AddBaseInfoForm(),
        'image_name_form': EditBaseImageNameForm()
    }
    return render(request, 'cloudclass/images.html', ctx)


@login_required
@require_GET
def ajax_base_image_list(request):
    base_images = BaseImage.objects.all()
    base_images = [{'name': image.name,
                    'id': image.id,
                    'img_url': image.get_os_img_url(),
                    'vm_id': image.extras.vm_id if image.extras else '',
                    'image_path': image.image_path,
                    'os_version': {'value': image.os_version, 'text': image.get_os_version_display()},
                    'os_type': {'value': image.os_type, 'text': image.get_os_type_display()},
                    'capacity': image.capacity,
                    'published': image.published}
                   for image in base_images]

    return JsonResponse({'result': base_images})


@login_required
@require_GET
def courses(request):
    new_course_id = request.GET.get('new_course_id')

    courses = [{'name': x.name, 'uuid': x.uuid, 'desc': x.desc, 'refname': x.refname,
                'os_version': x.get_os_version_display(),
                'img': x.get_os_img_url(), 'visibility': x.visibility,
                'id': x.id, 'profile': x.profile, 'image': x.image}
               for x in Course.objects.all().order_by('-priority')]
    form = CourseImageForm()

    ctx = {
        'courses': courses,
        'softftp': settingsutils.get_ftp_url(request, 'soft'),
        'imagesftp': settingsutils.get_ftp_url(request, 'images'),
        'form': form,
        'new_course_id': new_course_id
    }
    return render(request,'cloudclass/course.html',ctx)


@login_required
@require_POST
def ajax_edit_course_image(request):
    """ 修改课程镜像 """
    course_id = request.POST.get("course_id")
    form = CourseImageForm(course_id=course_id, data=request.POST)

    if courseutils.is_in_class(course_id):
        return JsonResponse({'result': 'error', 'message': '当前课程正在上课,不能修改'})

    if form.is_valid():
        form.save()
        return JsonResponse({"result": "ok"})
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({'result': 'error', 'message': message})


@login_required
@require_POST
def ajax_add_course_image(request):
    """新建课程镜像"""
    form = CourseImageForm(data=request.POST)

    if form.is_valid():
        dt = form.cleaned_data
        refname = u'{}.course'.format(uuid.uuid1())

        profile = CourseProfile.objects.get(pk=dt['profile'])

        base_image = BaseImage.objects.get(pk=dt['base_image'])
        image_path = os.path.join(os.path.dirname(base_image.image_path), refname)
        casapi.create_backing_volume(base_image.image_path, image_path)
        # 创建课程镜像
        course_image = CourseImage(
            parent=base_image,
            name=refname,
            capacity=base_image.capacity,
            image_path=image_path
        )

        host = Host.objects.last()
        vsid = OptsMgr.get_value(VSWITCH_ID)
        vsname = OptsMgr.get_value(VSWITCH_NAME)
        npp_info = casapi.get_npp_info(OptsMgr.get_value(NPP_NAME))
        hpid = casapi.get_hostpool()[u'id']

        msg = VirtDriver.instance().add_course(
                hpid, host.uuid, refname, course_image.image_path, dt['desc'], profile.cpu, 1,
                profile.memory, base_image.os_type, base_image.get_os_version_display(), '',
                vsid, vsname, npp_info['id'], 'none')

        if msg:
            course_image.save()
            course = form.save(image=course_image, refname=refname)
            VirtDriver.instance().get_vm_id(msg["msgId"], course)
            return JsonResponse({"result": "ok", 'new_course_id': course.id})
            # todo 挂载磁盘，并启动vm vnc中获取
        else:
            # 创建虚拟机失败时,删除volume
            rm(image_path)
            return JsonResponse({"result": "error", "message": u'创建虚拟机失败,请重试!'})
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({"result": "error", 'message': message})


@login_required
@require_POST
def ajax_add_course_image_and_open(request):
    """新建课程并打开vnc"""
    # todo: 重复,需要进行复用
    form = CourseImageForm(data=request.POST)

    if form.is_valid():
        dt = form.cleaned_data
        refname = u'{}.course'.format(uuid.uuid1())

        profile = CourseProfile.objects.get(pk=dt['profile'])

        base_image = BaseImage.objects.get(pk=dt['base_image'])
        image_path = os.path.join(os.path.dirname(base_image.image_path), refname)
        casapi.create_backing_volume(base_image.image_path, image_path)
        # 创建课程镜像
        course_image = CourseImage(
            parent=base_image,
            name=refname,
            capacity=base_image.capacity,
            image_path=image_path
        )

        host = Host.objects.last()
        vsid = OptsMgr.get_value(VSWITCH_ID)
        vsname = OptsMgr.get_value(VSWITCH_NAME)
        npp_info = casapi.get_npp_info(OptsMgr.get_value(NPP_NAME))
        hpid = casapi.get_hostpool()[u'id']

        msg = VirtDriver.instance().add_course(
                hpid, host.uuid, refname, course_image.image_path, dt['desc'], profile.cpu, 1,
                profile.memory, base_image.os_type, base_image.get_os_version_display(), '',
                vsid, vsname, npp_info['id'], 'none')

        if msg:
            course_image.save()
            course = form.save(image=course_image, refname=refname)
            VirtDriver.instance().get_vm_id(msg["msgId"], course)

            vm_id = course.uuid
            vm_name = course.refname
            status = VirtDriver.instance().get_vm_status(vm_id)
            if status != 'running':
                VirtDriver.instance().attach_share_image(vm_id, vm_name)
                task_info = casapi.start_vm(vm_id)
                casapi.wait_for_task(task_info['msgId'])
            vnc_info = casapi.get_vnc_info(vm_id)
            host_ip = vnc_info['ip']
            vnc_port = vnc_info['port']
            content = u'{}{}: {}:{}'.format(vm_name, vm_id, host_ip, vnc_port)
            fileutils.write_to_file(content, '/usr/local/noVNC/vnc_tokens/' + vm_name + ".conf")
            targetip = request.get_host().split(':')[0]
            data = {
                'vm_name': vm_name,
                'vm_id': vm_id,
                'ip': host_ip,
                'targetip': targetip,
                'result': 'ok'
            }
            return JsonResponse(data)
            # todo 挂载磁盘，并启动vm vnc中获取
        else:
            # 创建虚拟机失败时,删除volume
            rm(image_path)
            return JsonResponse({"result": "error", "message": u'创建虚拟机失败,请重试!'})
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({"result": "error", 'message': message})


@login_required
@require_POST
def ajax_add_base_image(request):
    """ 新建base镜像 """
    form = BaseImageForm(request.POST)
    iso_file_path = request.POST.get('os_iso')

    if not iso_file_path:
        return JsonResponse({'result': 'error', 'message': u'文件不存在'})

    if form.is_valid():
        data = form.cleaned_data
        refname = u'{}.base'.format(uuid.uuid1())

        host = Host.objects.last()
        vsid = OptsMgr.get_value(VSWITCH_ID)
        vsname = OptsMgr.get_value(VSWITCH_NAME)
        npp_info = casapi.get_npp_info(OptsMgr.get_value(NPP_NAME))
        hp_id = casapi.get_hostpool()[u'id']

        storpool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()
        image_path = u'{}/{}'.format(storpool, refname)

        base_img = form.save(image_path, refname=refname, commit=False)
        casapi.create_original_volume(image_path, base_img.capacity)

        try:
            msg = VirtDriver.instance().add_course(
                    hp_id, host.uuid, refname, image_path, data['name'], 2, 1, 2048,
                    base_img.os_type, base_img.get_os_version_display(),
                    iso_file_path, vsid, vsname, npp_info['id'], 'image')

            if msg:
                vm_id = VirtDriver.instance().get_base_image_vm_id(msg['msgId'])
                # 保存虚机{'vm_id': vm_id}进extras
                base_img.extras = BaseImageExtras(vm_id=vm_id)
                base_img.save()
                return JsonResponse({'result': 'ok', 'vm_id': vm_id, 'name': base_img.name, 'refname': base_img.refname})
            else:
                # 虚拟机创建失败删除volumn
                rm(image_path)
                return JsonResponse({'result': 'error', 'message': u'操作失败,请重试!'})
        except Exception, e:
            LOG.exception('Exception occurs: {}'.format(str(e)))
            return JsonResponse({'result': 'exception', 'message': u'系统异常,请稍候重试!'})
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({'result': 'error', 'message': message})


@login_required
@require_POST
def ajax_publish_base_image(request):
    """发布基础镜像"""
    vm_id = request.POST.get('vm_id')
    image_id = request.POST.get('image_id')

    if vm_id and image_id:
        # 删除虚机
        casapi.delete_vm(vm_id)
        # 标记base镜像为已发布,将虚机id设为None
        base_image = BaseImage.objects.get(id=image_id)
        base_image.published = True
        base_image.extras.vm_id = None
        base_image.save()
        return JsonResponse({'result': 'ok'})
    else:
        return JsonResponse({'result': 'error', 'message': u'操作失败,请稍候重试!s'})


@login_required
@require_POST
def ajax_del_base_image(request):
    """删除基础镜像"""
    image_id = request.POST.get('image_id')
    base_image = BaseImage.objects.get(id=image_id)
    ret = {'result': 'ok'}

    if image_id:
        course_images = CourseImage.objects.filter(parent=base_image)
        if course_images:
            # 有基于该镜像的课程,不能删除
            ret['result'] = 'have_course'
            ret['message'] = u'有基于该镜像的课程,不能删除！'
        else:
            if not base_image.published:
                # 删除虚机与磁盘
                host_id = casapi.get_host()['id']
                vm_info = casapi.get_vms_by_name(host_id, base_image.refname)
                if vm_info:
                    casapi.delete_vm(vm_info['id'])
            # 已经发布的镜像虚机已经被删除
            # 从硬盘删除磁盘
            rm('-f', base_image.image_path)

            # 移除数据库记录
            base_image.delete()
    else:
        ret['result'] = 'error'
        ret['message'] = u'该镜像不存在,请刷新页面!'
    return JsonResponse(ret)


@login_required
@require_POST
def ajax_get_os_version_by_image_id(request):
    """根据镜像id获取os_version"""
    image_id = request.POST.get("image_id")
    base_image = BaseImage.objects.get(id=image_id)
    return JsonResponse({"os_version": base_image.get_os_version_display()})


@login_required
@require_POST
def add_base_image_info(request):
    """
    给基础镜像添加或修改基本信息
    """
    image_id = request.POST.get('image_id')
    os_type = request.POST.get('os_type')
    os_version = request.POST.get('os_version')
    capacity = request.POST.get('capacity')
    name = request.POST.get('name')

    form = AddBaseInfoForm(image_id=image_id, data={'os_type': os_type, 'os_version': os_version, 'capacity': capacity, 'name': name})
    if form.is_valid():
        base_image = form.save()
        desc = base_image.name
        refname = base_image.refname
        storpool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()
        fpath = u'{}/{}'.format(storpool, refname)

        # 更改硬盘大小
        casapi.resize_volume(fpath, int(capacity))

        # 创建虚机
        host = Host.objects.last()
        vsid = OptsMgr.get_value(VSWITCH_ID)
        vsname = OptsMgr.get_value(VSWITCH_NAME)
        npp_info = casapi.get_npp_info(OptsMgr.get_value(NPP_NAME))
        hp_id = casapi.get_hostpool()[u'id']

        msg = casapi.create_vm(host.uuid, hp_id, refname, desc, 2048, 2, 1, base_image.os_type,
                               base_image.get_os_version_display(), fpath, vsid,
                               vsname, npp_info['id'], fpath, 'none')
        if msg['msgId']:
            LOG.debug('msg={}'.format(msg))
            vm_id = VirtDriver.instance().get_base_image_vm_id(msg['msgId'])
            # 保存虚机{'vm_id': vm_id}进extras
            base_image.extras = BaseImageExtras(vm_id=vm_id)
            base_image.save()
        return JsonResponse({'result': 'ok'})
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({'result': 'error', 'message': message})


@require_GET
def ajax_course_list(request):
    courses = [{'name': x.desc or x.name,
                'uuid': x.uuid,
                'desc': x.desc,
                'profie_id': x.profile.id,
                'image_id': x.image.parent.id,
                'os_type': {'value': x.os_type, 'text': x.get_os_type_display()},
                'os_version': {'value': x.os_version, 'text': x.get_os_version_display()},
                'img_url': x.get_os_img_url(),
                'refname': x.refname,
                'visibility': x.visibility}
               for x in Course.objects.all().order_by('-priority')]
    return JsonResponse({"result": courses})


@require_POST
def ajax_course_images(request):
    id = request.POST.get("id")
    try:
        base_img = BaseImage.objects.get(id=id)

        os_version = base_img.get_os_version_display()
    except BaseImage.DoesNotExist:
        os_version = "error"

    return JsonResponse({"result": os_version})


@login_required
@require_GET
def desktop_list(request):
    return render(request, 'cloudclass/desktop.html')


@login_required
def ajax_get_desktops(request):
    desktops = []
    for item in Desktop.objects.all():
        _, index = item.name.rsplit('_', 1)
        try:
            tmac = cacheutils.get_tns()[int(index)]
            terminal = Terminal.objects.get(mac_address=tmac)
            terminal_ip_address = terminal.ip_address
            terminal_mac_address = terminal.mac_address
            terminal_name = terminal.name
        except:
            terminal_ip_address = ''
            terminal_mac_address = ''
            terminal_name = ''
        d = {
            'name': item.name,
            'macaddr': item.mac_address,
            'ipaddr': item.ip_address,
            'id': item.uuid,
            'tip': terminal_ip_address,
            'tmac': terminal_mac_address,
            'tname': terminal_name
        }
        desktops.append(d)
    ctx = {'desktops': desktops}
    return JsonResponse(ctx)


@login_required
@require_GET
def network_list(request):
    try:
        network = Network.objects.get(name='default')
    except Network.DoesNotExist:
        host = Host.objects.last()
        vs_info = casapi.get_vswitch_info(host.uuid, OptsMgr.get_value(VSWITCH_NAME))
        segment = IP(vs_info['address']).make_net(vs_info['netmask'])
        address_begin = IP(segment.int() + 1)
        address_end = IP(segment.broadcast().int() - 1)

        kwargs = {
            'name': 'default',
            'address_begin': address_begin.strNormal(),
            'address_end': address_end.strNormal(),
            'netmask': vs_info['netmask']
        }
        if vs_info['gateway']:
            kwargs['gateway'] = vs_info['gateway']
        network = Network.objects.create(**kwargs)
        LOG.warning('Failed to get network, auto create one: %s' % network)
    is_running = dhcputils.Dnsmasq.is_running()
    return render(request, 'cloudclass/network.html', {"network": network, 'dhcp_is_running': is_running})


@login_required
@require_GET
def teacher_list(request):
    if request.user.is_superuser:
        teacher_qs = User.objects.all().filter(is_active=1, is_superuser=False)
    else:
        teacher_qs = User.objects.filter(id=request.user.id)
    form = TeacherForm()
    editform = TeacherEditForm()

    ctx = {
        'teachers': teacher_qs,
        'form': form,
        'editform': editform,
        'user': request.user
    }
    return render(request, 'cloudclass/teacher.html', ctx)


@login_required
@require_GET
def vnc_view(request):
    vmname = request.GET.get('name')
    vmid = request.GET.get('uuid')
    ip = request.GET.get('ip')
    targetip = request.GET.get('targetip')

    ctx = {
        'name': vmname,
        'vmid': vmid,
        'ip': ip,
        'targetip': targetip,
    }
    return render(request, 'cloudclass/vnc.html', ctx)


@login_required
@require_POST
def ajax_start_vnc(request):
    vmname = request.POST.get('name')

    vm_type = request.POST.get('type')
    if vm_type == 'course':
        try:
            course = Course.objects.get(refname=vmname)
            if courseutils.is_in_class(course.id):
                return JsonResponse({'result': 'error', 'message': u'当前课程正在上课,不能安装软件!'})
        except Course.DoesNotExist:
            return JsonResponse({'result': 'error', 'message': u'操作失败,请稍后重试'})

    vmid = request.POST.get('uuid')
    features = request.POST.get('features').split(',')
    if vmid and vmname:
        status = VirtDriver.instance().get_vm_status(vmid)
        if status != 'running':
            if 'share' in features:
                VirtDriver.instance().attach_share_image(vmid, vmname)
            task_info = casapi.start_vm(vmid)
            casapi.wait_for_task(task_info['msgId'])
        vnc_info = casapi.get_vnc_info(vmid)
        host_ip = vnc_info['ip']
        vnc_port = vnc_info['port']
        content = u'{}{}: {}:{}'.format(vmname, vmid, host_ip, vnc_port)
        fileutils.write_to_file(content, '/usr/local/noVNC/vnc_tokens/' + vmname + ".conf")
        targetip = request.get_host().split(':')[0]
        data = {
            'name': vmname,
            'vmid': vmid,
            'ip': host_ip,
            'targetip': targetip,
            'result': 'ok'
        }
        return JsonResponse(data)
    return JsonResponseBadRequest({
        'message': u'Does not give the name or uuid.'
    })


@login_required
@require_POST
def ajaxdelbatch_desktop(request):
    """批量删除桌面"""
    ids = request.POST.get("ids").split(',')
    LOG.debug("Batch_ids = %s " % ids)
    listid = []
    for id in ids:
        listid.append(id)
    LOG.debug("Listid = %s" % listid)
    desktops = Desktop.objects.filter(uuid__in=listid)
    LOG.debug("desktops: %s" % desktops)

    VirtDriver.instance().delete_desktops(desktops)

    return JsonResponse({'ids': ids})


@login_required
@require_POST
def ajax_get_isos(request):
    isos = fileutils.get_isos(settings.ISOS_PATH)
    return JsonResponse({'isos': isos})


@login_required
@require_POST
def ajax_get_softs(request):
    softs = fileutils.get_softs(settings.DEFAULT_SHARE_IMAGE['defaultdir'])
    return JsonResponse({'softs': softs})


@login_required
@require_POST
def ajax_get_upgrades(request):
    path = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    upgrades = fileutils.get_upgrades(os.path.join(path, "static/upgrade"))
    return JsonResponse({'result': upgrades})


@login_required
@require_POST
def ajax_del_upgrades(request):
    path = os.path.join(os.getcwd(), "/static/upgrade")
    fileutils.del_iso(path, request.POST.get('name'))
    return JsonResponse({})


@login_required
@require_POST
def ajaxdel_iso(request):
    fileutils.del_iso(settings.ISOS_PATH, request.POST.get('name'))
    return JsonResponse({})


@require_POST
@csrf_exempt
def upload_files(request):  # 附件：上传
    type = request.POST.get("type")
    if request.is_ajax():
        # the file is stored raw in the request
        upload = request
        is_raw = True
        # AJAX Upload will pass the filename in the querystring if it is
        # the "advanced" ajax upload
        try:
            filename = request.GET['qqfile']
        except KeyError:
            return HttpResponseBadRequest("AJAX request not valid")
            # not an ajax upload, so it was the "basic" iframe version with
            # submission via form
    else:
        is_raw = False
        if len(request.FILES) == 1:
            # FILES is a dictionary in Django but Ajax Upload gives the uploaded file an
            # ID based on a random number, so it cannot be guessed here in the code.
            # Rather than editing Ajax Upload to pass the ID in the querystring,
            # observer that each upload is a separate request,
            # so FILES should only have one entry.
            # FILES is a dictionary in Django but Ajax Upload gives the
            # uploaded file an ID based on a random number, so it cannot be
            # guessed here in the code. Rather than editing Ajax Upload to
            # pass the ID in the querystring, observer that each upload is
            # a separate request, so FILES should only have one entry.
            # Thus, we can just grab the first (and only) value in the dict.
            upload = request.FILES.values()[0]

    filename = upload.name
    # save the file
    newdoc = {'name': filename, 'type': 'iso', 'filepath': '', "success": False,
              'contentlength': '0'}
    docinfo = save_upload(upload, filename, is_raw, newdoc, type)

    strpath = str(docinfo["filepath"])
    contentsize = docinfo["contentlength"]
    # let Ajax Upload know whether we saved it or not
    ret_json = {'success': docinfo["success"], 'contentlength': contentsize,
                'filename': filename, 'filepath': strpath}
    return JsonResponse(ret_json)


def save_upload(uploaded, filename, raw_data, newdoc, type):
    try:
        save_path = settings.ISOS_PATH
        if type == "3":
            save_path = settings.DEFAULT_SHARE_IMAGE["defaultdir"]
        save_url = save_path

        if not os.path.isdir(save_path):
            os.makedirs(save_path)
        ext = uploaded.name.split('.').pop()

        new_file = filename
        file_path = os.path.join(save_path, new_file)
        with open(file_path, 'wb+') as f:
            for chunk in uploaded.chunks():
                f.write(chunk)

        # calc file size
        file_len = os.path.getsize(file_path)
        newdoc["filepath"] = save_url
        newdoc["filename"] = filename
        newdoc["contentlength"] = file_len
        newdoc["success"] = True

        LOG.debug("new_doc_info, save_url = %s, filename = %s, file_len = %s" % (save_url, filename, file_len))
    except:
        LOG.exception('We meet error!')
    return newdoc


@login_required
@require_POST
def ajax_del_course(request):
    course_id = request.POST.get('course_id')

    if courseutils.is_in_class(course_id):
        return JsonResponse({'result': 'error', 'message': u'该课程正在上课,无法删除'})

    try:
        course = Course.objects.get(id=course_id)
        VirtDriver.instance().delete_course(course)
        return JsonResponse({'result': 'ok'})
    except:
        LOG.exception('Failed to get course[{}]'.format(course_id))
        return JsonResponse({'result': 'error', 'message': u'操作失败,请稍后重试'})


def ajax_get_host_monitor(request):

    if not request.user.is_authenticated():
        return JsonResponse({'authed': False})

    host = Host.objects.last()
    monitor_info = VirtDriver.instance().get_host_monitor(host.uuid)

    summary = VirtDriver.instance().get_host_summary(host.uuid)
    host_info = {
        'ip': summary.get(u'IP\u5730\u5740') or summary.get(u'IP Address'),
        'hostname': summary.get(u'\u4e3b\u673a\u578b\u53f7') or summary.get(u'Model'),
        'cpucount': summary.get(u'CPU\u6570\u91cf') or summary.get(u'CPUs'),
        'cpumodel': summary.get(u'CPU\u578b\u53f7') or summary.get(u'CPU Model'),
        'cpufrequence': summary.get(u'CPU\u4e3b\u9891') or summary.get(u'CPU Frequency'),
        'mem': summary.get(u'\u5185\u5b58') or summary.get(u'Memory'),
        'hoststatus': summary.get(u'image'),
        'cvkversion': summary.get(u'\u7248\u672c') or summary.get(u'Version'),
        'runtime': summary.get(u'\u7cfb\u7edf\u8fd0\u884c\u65f6\u95f4') or summary.get(u'System Uptime'),
    }
    d = {
        'cpu': monitor_info.get(u'cpuRate'),
        'mem': monitor_info.get(u'memRate'),
        'disktotal': summary.get(u'\u4e3b\u673a\u672c\u5730\u5b58\u50a8') or summary.get(u'Local Storage'),
        'diskrate': summary.get(u'diskRate'),
        'vmtotal': summary.get(u'total'),
        'vmrun': summary.get(u'run'),
        'hostinfo': host_info,
    }
    return JsonResponse({"rsp": d, 'authed': True})


@login_required
@require_POST
def ajax_add_teacher(request):
    form = TeacherForm(request.POST)

    if form.is_valid():
        form.save()
        return JsonResponse({'result': 'ok'})
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({'result': 'error', 'message': message})


@login_required
@require_POST
def ajax_edit_teacher(request):
    form = TeacherEditForm(request.POST)

    if form.is_valid():
        form.save()
        return JsonResponse({'result': 'ok'})
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({'result': 'error', 'message': message})


@login_required
@require_POST
def ajax_del_teacher(request):
    teacher_id = request.POST.get("teacher_id")
    
    try:
        teacher = User.objects.get(id=teacher_id, is_superuser=False)
        teacher.delete()
        return JsonResponse({'result': 'ok'})
    except User.DoesNotExist:
        return JsonResponse({'result': 'error', 'message': u'要删除的用户不存在'})


@login_required
@require_POST
def ajax_add_network(request):
    ip_address_begin = request.POST.get('ip_address_begin')
    ip_address_end = request.POST.get('ip_address_end')
    netmask = request.POST.get('netmask')
    gateway = request.POST.get('gateway')
    dns = request.POST.get('dns')

    # check arguments
    try:
        address_begin = IP(ip_address_begin)
        address_end = IP(ip_address_end)
        segment1 = address_begin.make_net(netmask)
        segment2 = address_end.make_net(netmask)
    except ValueError as e:
        return JsonResponseBadRequest({'result': 'error', 'message': e.message})
    if segment1 != segment2:
        return JsonResponseBadRequest({
            'message': u'开始地址和结束地址必须在同一网段',
            'result': 'error'
        })
    if address_begin > address_end:
        return JsonResponseBadRequest({
            'message': u'开始地址必须小于结束地址',
            'result': 'error'
        })

    if gateway:
        try:
            gateway = IP(gateway)
        except ValueError as e:
            return JsonResponseBadRequest({'result': 'error', 'message': e.message})
    else:
        gateway = None

    if dns:
        try:
            dns = IP(dns)
        except ValueError as e:
            return JsonResponseBadRequest({'result': 'error', 'message': e.message})
    else:
        dns = None

    network, _ = Network.objects.update_or_create(defaults={
        'address_begin': address_begin.strNormal(),
        'address_end': address_end.strNormal(),
        'netmask': segment1.strNetmask(),
        'gateway': gateway and gateway.strNormal(),
        'dns': dns and dns.strNormal(),
    }, name='default')

    pairs = {}
    for i in xrange(0, settingsutils.get_desktop_count() + 1):
        tmpaddr = IP(address_begin.int() + i + 1)  # address_begin + 1 for teacher
        if tmpaddr > address_end:
            break
        pairs[random_mac(0x00, MAC_TYPE_VM, i)] = tmpaddr.strNormal()
    dhcputils.config_dhcp_service(
        OptsMgr.get_value(VSWITCH_NAME),
        OptsMgr.get_value(VLAN_TAG),
        network.address_begin,
        network.address_end,
        network.netmask,
        network.gateway,
        network.dns,
        pairs,
        'infinite')
    return JsonResponse({'result': 'ok'})


@login_required
@require_POST
def ajax_start_dhcp_service(request):
    # dhcputils.DhcpConf.clean_lease_file()
    dhcputils.Dnsmasq.start_service()
    return HttpResponseNoContent()


@login_required
@require_POST
def ajax_stop_dhcp_service(request):
    dhcputils.Dnsmasq.stop_service()
    # dhcputils.DhcpConf.clean_lease_file()
    return HttpResponseNoContent()


@login_required
@require_POST
def ajax_get_course(request):
    uuid = request.POST.get("id")
    type = request.POST.get("type")
    course_info = Course.objects.get(uuid=uuid)
    LOG.debug("uuid = %s, type = %s, \nCourse_info = %s" % (uuid, type, course_info))
    d = dict()
    d["name"] = course_info.name
    d["desc"] = course_info.desc
    d["os_type"] = course_info.os_type
    d["os_version"] = course_info.os_version
    d["profileid"] = course_info.profile_id
    d["visibility"] = course_info.visibility
    LOG.debug("Response info = %s" % d)
    return JsonResponse({"rsp": d})


@login_required
@require_POST
def ajax_del_file(request):
    type = request.POST.get("type")
    name = request.POST.get("name")
    if type == "1":
        fileutils.del_iso(settings.ISOS_PATH, name)
    else:
        fileutils.del_iso(settings.DEFAULT_SHARE_IMAGE["defaultdir"], name)
    return JsonResponse({"result": "ok"})


@login_required
@require_GET
def change_pwd(request):
    return render(request, 'cloudclass/changepwd.html')


@login_required
@require_POST
def ajax_change_pwd(request):
    ret = {'result': 'ok'}
    form = PasswordChangeForm(request, request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse(ret)
    else:
        errors = form.errors
        message = form_error_msg(errors)
        ret['result'] = 'errors'
        ret['message'] = message

    return JsonResponse(ret)


@login_required
@require_GET
def ajax_get_dashboard(request):
    hostinfo = Host.objects.last()
    LOG.debug("Hostinfo.uuid = %s " % hostinfo.uuid)
    vm_count = 0
    vm_run = 0
    if hostinfo:
        vminfo = VirtDriver.instance().get_all_vms(hostinfo.uuid)
        vm_count = vminfo["vm_all"]
        vm_run = vminfo["vm_run"]
        LOG.debug("vminfo['vm_all'] = %s, vminfo['vm_run'] = %s" % (vm_count, vm_run))

    return JsonResponse({"vm_count": vm_count, "vm_run": vm_run})


@login_required
@require_POST
def ajax_remove_disk(request):
    vm_id = request.POST.get('id')
    vm_name = request.POST.get('name')
    VirtDriver.instance().shut_vm_and_remove_disk(vm_id, vm_name)
    return JsonResponse({'result': 'ok'})


@login_required
@require_POST
def ajax_close_vm(request):
    vm_id = request.POST.get('id')
    VirtDriver.instance().shutdown_vm(vm_id)
    return JsonResponse({'result': 'ok'})


@login_required
@require_POST
def ajax_reboot_host(request):
    try:
        VirtDriver.instance().reboot_host(None)
    except:
        LOG.exception('failed to reboot host')

    return JsonResponse({"result": "ok"})


@login_required
@require_POST
def ajax_shutoff_host(request):
    try:
        VirtDriver.instance().shutoff_host(None)
    except:
        LOG.exception('failed to shutdown host')
    return JsonResponse({"result": "ok"})


@login_required
@require_POST
def ajax_check_course_name(request):  # 检查课程名称是否重复
    name = request.POST.get("name")
    try:
        Course.objects.get(name=name)
        return JsonResponse({'result': 'error', 'message': u'该课程名称已经存在'})
    except Course.DoesNotExist:
        return JsonResponse({'result': 'ok'})


@login_required
@require_GET
def get_logs(request):
    logfile = fileutils.collect_logs()
    rsp = HttpResponse(FileWrapper(logfile))
    rsp['Content-Disposition'] = 'attachment; filename=hcc_log.zip'
    rsp['Content-Type'] = 'application/zip'
    return rsp


@login_required
@require_GET
def logs(request):
    return render(request, "cloudclass/logs.html")


@login_required
@require_POST
def ajax_edit_settings(request):
    res = {}
    try:
        desktop_count = request.POST.get('desktop_count')

        if int(desktop_count) > settingsutils.get_max_users():
            return JsonResponse({'result': 'error', 'message': u'桌面数量不能超过最大值'})

        cas_address = request.POST.get('cas_address')
        cas_username = request.POST.get('cas_username')
        cas_password = request.POST.get('cas_password')

        auth = HTTPDigestAuth(cas_username, cas_password)
        auth = {
            'auth': auth,
            'baseurl': cas_address
        }

        host_id = casapi.get_host(**auth)[u'id']

        white_list = request.POST.get('white_list')
        white_list = white_list.replace(u'，', ',').split(',')
        white_list = ','.join([i.strip() for i in white_list if i])

        vswitch_id = request.POST.get('vswitch')
        npp_id = request.POST.get('npp')
        acl_id = request.POST.get('acl', None)

        all_vswitches = casapi.get_all_vswitches(host_id, **auth)
        for v in all_vswitches:
            if v['id'] == str(vswitch_id):
                vswitch_name = v['name']
                break

        all_npps = casapi.get_all_profiles(**auth)
        for n in all_npps:
            if n['id'] == str(npp_id):
                npp_name = n['name']
                break

        npp_info = casapi.get_npp_info(npp_name, **auth)

        if 'aclStrategyId' in npp_info:
            npp_info.pop('aclStrategyId')
        if 'aclName' in npp_info:
            npp_info.pop('aclName')

        if acl_id:
            acl_info = casapi.get_acl_info(acl_id, **auth)
            acl_name = acl_info['name']
        else:
            acl_name = ''

        # 设置网络策略模板,添加acl
        x = casapi.add_acl_to_profile(npp_info, acl_id, acl_name, **auth)

        if x.status_code == 204:
            res['result'] = 'ok'
            OptsMgr.set_value(DESKTOP_COUNT, desktop_count)
            OptsMgr.set_value(CAS_ADDRESS, cas_address)
            OptsMgr.set_value(CAS_USERNAME, cas_username)
            OptsMgr.set_value(CAS_PASSWORD, cas_password)
            OptsMgr.set_value(ACL_WHITELIST, white_list)
            OptsMgr.set_value(VSWITCH_ID, vswitch_id)
            OptsMgr.set_value(VSWITCH_NAME, vswitch_name)
            OptsMgr.set_value(NPP_ID, npp_id)
            OptsMgr.set_value(NPP_NAME, npp_name)
            OptsMgr.set_value(ACL_ID, acl_id)
            OptsMgr.set_value(ACL_NAME, acl_name)

            reload(casapi)
        else:
            res['result'] = 'error'
            res['message'] = u'设置出错,请重试~'
    except Exception, e:
        LOG.error(str(e))
        res['result'] = 'error'

        if 'Unauthorized' in str(e):
            res['message'] = u'CAS用户名或密码错误'
        else:
            res['message'] = u'服务器错误,请稍后重试~'

    return JsonResponse(res)


@login_required
@require_GET
def sys_upgrade(request):
    ctx = {
        'upgradeftp': settingsutils.get_ftp_url(request, 'upgrade')
    }
    return render(request, "cloudclass/sysupgrade.html", ctx)


@login_required
@require_GET
def sys_settings(request):
    ret = {
        'max_desktop_count': settingsutils.get_max_users(),
        'desktop_count': {'default': settingsutils.get_desktop_count()},
        'cas_address': {'default': OptsMgr.get_value(CAS_ADDRESS)},
        'cas_username': {'default': OptsMgr.get_value(CAS_USERNAME)},
        'cas_password': {'default': OptsMgr.get_value(CAS_PASSWORD)}}

    try:
        casapi.test_conn()
        is_conn = True
    except Exception, e:
        LOG.error(str(e))
        is_conn = False
    ret['is_conn'] = is_conn
    if is_conn:
        ret['white_list'] = {'default': OptsMgr.get_value(ACL_WHITELIST)}

        host_id = casapi.get_host()[u'id']
        vswitchs = casapi.get_all_vswitches(host_id)
        vswitch_list = [{'id': v['id'], 'name': v['name']} for v in vswitchs]
        ret['vswitch'] = {'choices': vswitch_list, 'default': OptsMgr.get_value(VSWITCH_NAME)}

        npps = casapi.get_all_profiles()
        npp_list = [{'id': n['id'], 'name': n['name']} for n in npps]
        ret['npp'] = {'choices': npp_list, 'default': OptsMgr.get_value(NPP_NAME)}

        acls = casapi.get_acls()
        acl_list = [{'id': a['@id'], 'name': a['name']} for a in acls]
        ret['acl'] = {'choices': acl_list, 'default': OptsMgr.get_value(ACL_NAME)}

    return render(request, 'cloudclass/syssettings.html', ret)


@login_required
@require_POST
def ajax_reload_cas_settings(request):
    cas_address = request.POST.get('cas_address')
    cas_username = request.POST.get('cas_username')
    cas_password = request.POST.get('cas_password')

    auth = HTTPDigestAuth(cas_username, cas_password)
    auth = {
        'auth': auth,
        'baseurl': cas_address
    }
    ret = {}
    try:
        casapi.request('get', '/cas/casrs/profile/', **auth)
        host_id = casapi.get_host(**auth)[u'id']
        vswitchs = casapi.get_all_vswitches(host_id, **auth)
        vswitch_list = [{'id': v['id'], 'name': v['name']} for v in vswitchs]
        vs_t = Template(
            u"""
            <select name="vswitch" id="id_vswitch" class="form-control">
                <option value="">----</option>
                {% for v in choices %}
                    <option value="{{ v.id }}">{{ v.name }}</option>
                {% endfor %}
            </select>
            <span class="help-inline"></span>
            """
        )
        vs_c = Context({
            'choices': vswitch_list
        })
        ret['vswitch_block'] = vs_t.render(vs_c)

        npps = casapi.get_all_profiles(**auth)
        npp_list = [{'id': n['id'], 'name': n['name']} for n in npps]
        npp_t = Template(
            u"""
            <select name="npp" id="id_npp" class="form-control">
                {% for n in choices %}
                    <option value="{{ n.id }}">{{ n.name }}</option>
                {% endfor %}
            </select>
            <span class="help-inline"></span>
            """
        )
        npp_c = Context({
            'choices': npp_list
        })
        ret['npp_block'] = npp_t.render(npp_c)

        acls = casapi.get_acls(**auth)
        acl_list = [{'id': a['@id'], 'name': a['name']} for a in acls]
        acl_t = Template(
            u"""
            <select name="acl" id="id_acl" class="form-control">
                <option value="">----</option>
                {% for a in choices %}
                    <option value="{{ a.id }}">{{ a.name }}</option>
                {% endfor %}
            </select>
            <span class="help-inline">若为空将不能使用禁网功能,建议添加ACL</span>
            """
        )
        acl_c = Context({
            'choices': acl_list
        })
        ret['acl_block'] = acl_t.render(acl_c)
        ret['result'] = 'ok'
        return JsonResponse(ret)
    except requests.RequestException, e:
        LOG.error(str(e))
        if '403' in str(e):
            # 非法访问cas会返回403 Forbidden
            ret['code'] = 403
            ret['message'] = u'CAS设置发生修改,暂时无法连接,请5分钟后再进行操作'
        else:
            ret['message'] = u'CAS无法连接,请检查设置是否正确'
        ret['result'] = 'error'
        return JsonResponse(ret)


@login_required
@require_POST
def ajax_install_castools(request):
    vm_id = request.POST.get("vm_id")
    vm_name = request.POST.get("vm_name")
    vm_path = "/vms/isos/castools.iso"
    type = request.POST.get("type")  # 完全安装的时候进行安装castools

    result = VirtDriver.instance().install_castools(vm_id, vm_name, vm_path,type)
    str = "error"
    if result:
        if not type:
            VirtDriver.instance().reboot_vm(vm_id)
        str = "ok"
    return JsonResponse({"result": str})


@login_required
@require_GET
def license(request):
    lic = cacheutils.get_license()
    if lic is None:
        context = {
            'max_users': 70,
            'expire_days': cacheutils.get_trail()
        }
    else:
        context = {
            'max_users': lic.max_users,
            'barcode': lic.barcode,
            'expire_days': lic.expire_days,
        }
    return render(request, 'cloudclass/license.html', context)


@login_required
@require_GET
def get_host_info(request):
    name = request.GET.get('name')
    country = request.GET.get('country')
    province = request.GET.get('province')
    company = request.GET.get('company')
    email = request.GET.get('email')
    phone = request.GET.get('phone')

    # TODO check arguments
    macs = cacheutils.get_nics()[:3]  # 最多取三个
    content = fileutils.generate_host_info(name, country, province, company,
                                           email, phone, macs)
    rsp = HttpResponse(content)
    rsp['Content-Disposition'] = 'attachment; filename=host.info'
    rsp['Content-Type'] = 'application/octet-stream'
    return rsp


@login_required
@require_POST
@csrf_exempt
def upload_license(request):
    if request.is_ajax():
        # the file is stored raw in the request
        upload = request
        is_raw = True
        # AJAX Upload will pass the filename in the querystring if it is
        # the "advanced" ajax upload
        try:
            if 'qqfile' in request.GET:
                filename = request.GET['qqfile']
            else:
                filename = request.REQUEST['qqfilename']
        except KeyError:
            return HttpResponseBadRequest('AJAX request not valid')
    # not an ajax upload, so it was the "basic" iframe version with
    # submission via form
    else:
        is_raw = False
        if len(request.FILES) == 1:
            # FILES is a dictionary in Django but Ajax Upload gives
            # the uploaded file an ID based on a random number, so it
            # cannot be guessed here in the code. Rather than editing
            # Ajax Upload to pass the ID in the querystring, observe
            # that each upload is a separate request, so FILES should
            # only have one entry. Thus, we can just grab the first
            # (and only) value in the dict.
            upload = request.FILES.values()[0]
        else:
            return HttpResponseBadRequest("Bad Upload")
        filename = upload.name

    content = fileutils.get_content(upload, filename, is_raw)
    if content is None:
        return JsonResponse({'code': 3000, 'message': u'授权文件无法识别'})

    try:
        lic1 = fileutils.import_license(content)
    except:
        LOG.exception('failed to parse license: %s' % content)
        return JsonResponse({'code': 3000, 'message': u'授权文件无法识别'})

    if fileutils.validate_license(lic1, cacheutils.get_nics()):
        # 授权文件有效，接下来判断是否需要更新
        lic2 =  cacheutils.get_license()
        if lic2 is None:
            # 试用，没有上传过授权文件，直接更新 license
            pass
        else:
            # 上传过授权文件
            ats1 = [x.authtype for x in lic1.auths]
            ats2 = [x.authtype for x in lic2.auths]
            if '0' not in ats1 and '0' in ats2:
                # 尝试用临时授权覆盖正式授权
                return JsonResponse({'code': 3000, 'message': u'已经是正式授权，不能激活临时授权'})
        OptsMgr.set_value(ACTIVATION_LICENSE, content)
        cacheutils.clear_license()
        return JsonResponse({'code': 0})
    else:
        return JsonResponse({'code': 3000, 'message': u'授权无效或者已经过期。'})


@require_POST
@csrf_exempt
def vnc_operate(request):
    otype = request.POST.get('operateType')
    vm_id = request.POST.get('id')
    vm_name = request.POST.get('domainName')
    if vm_id:
        if otype == '0':  # start
            VirtDriver.instance().power_on_vm(vm_id)
        elif otype == '1':  # shutoff
            VirtDriver.instance().shut_vm_and_remove_disk(vm_id, vm_name)
        elif otype == '2':  # close
            VirtDriver.instance().force_power_off_vm(vm_id)
        elif otype == '4':
            status = VirtDriver.instance().get_vm_status(vm_id)
            return JsonResponse({'result': status})
    return JsonResponse({'result': 'success'})


@require_POST
@csrf_exempt
def ajax_vm_operate(request):
    ids = request.POST.get("ids")
    type = request.POST.get("type")
    for id in ids.split(","):
        if type == "poweroff":
            VirtDriver.instance().power_off_vm(id)
        elif type == "start":
            VirtDriver.instance().power_on_vm(id)
    return JsonResponse({"result": "ok"})


def init_guide(request, step):
    context = {'step': int(step)}

    if int(step) == 2:
        host_name = re.findall(r'[0-9]+(?:\.[0-9]+){3}', OptsMgr.get_value(CAS_ADDRESS))[0]
        context['host_name'] = host_name
    elif int(step) == 3:
        hostid = casapi.get_host()['id']
        pnics = casapi.get_pnics(hostid=hostid)
        context['pnics'] = pnics

        vswitches = casapi.get_all_vswitches(hostid=hostid)
        context['vswitches'] =vswitches
        if not pnics:
            vswitches = casapi.get_all_vswitches(hostid=hostid)
            context['vswitches'] =vswitches

    return render(request, 'cloudclass/init_guide.html', context)


@require_POST
@csrf_exempt
def set_host(request):
    hostpool = request.POST.get('hostpool', '').strip()
    host_name = request.POST.get('host_name', '').strip()
    host_username = request.POST.get('host_username', '').strip()
    host_password = request.POST.get('host_password', '').strip()

    cas_ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', OptsMgr.get_value(CAS_ADDRESS))[0]

    res = {'result': 'ok'}
    if hostpool and host_name and host_username and host_password and cas_ip == host_name:
        try:
            # 创建主机池
            casapi.create_hostpool(hostpool)
        except casapi.exceptions.HostPoolAlreadyExist:
            LOG.info('HostPool already exists')
        except Exception, e:
            LOG.error(str(e))
            res['result'] = 'error'
            res['message'] = u'创建主机池失败！请检查设置是否正确'

        try:
            hp_id = casapi.get_hostpool()[u'id']
            # 创建主机
            casapi.create_host(hp_id, host_name, host_username, host_password, True)
        except casapi.exceptions.HostAlreadyExist:
            LOG.info('Host already exists')
        except Exception, e:
            LOG.error(str(e))
            res['result'] = 'error'
            res['message'] = u'创建主机失败！请检查设置是否正确'

        if res['result'] == 'ok':
            OptsMgr.set_value(CAS_HOSTPOOL, hostpool)
            OptsMgr.set_value(SSH_ADDRESS, host_name)
            OptsMgr.set_value(SSH_USERNAME, host_username)
            OptsMgr.set_value(SSH_PASSWORD, host_password)
    else:
        res['result'] = 'error'
        res['message'] = u'操作失败！请检查设置是否正确'
    return JsonResponse(res)


@require_POST
@csrf_exempt
def stack_backends(request):
    cas_address = request.POST.get('cas_address', None)
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

    res = {}
    if cas_address and username and password:

        auth = HTTPDigestAuth(username, password)
        auth = {
            'auth': auth,
            'baseurl': cas_address
        }
        try:
            casapi.request('get', '/cas/casrs/profile/', **auth)
            OptsMgr.set_value(CAS_ADDRESS, cas_address)
            OptsMgr.set_value(CAS_USERNAME, username)
            OptsMgr.set_value(CAS_PASSWORD, password)

            res['result'] = 'ok'
            reload(casapi)
        except requests.RequestException:
            res['result'] = 'error'
            res['message'] = u'服务器错误,请稍候重试!'
            LOG.exception('We meet exception')
    else:
        res['result'] = 'error'
        res['message'] = u'认证失败,请确保填写正确!'
    return JsonResponse(res)


@require_POST
@csrf_exempt
def param_set(request):
    res = {'result': 'ok'}
    custom = request.POST.get('custom')
    white_list = request.POST.get('white_list')
    vswitch_name = request.POST.get('vswitch_name')
    npp_name = request.POST.get('npp_name')
    acl_name = request.POST.get('acl_name')
    vlan_tag = request.POST.get('vlan')
    vlan_tag = int(vlan_tag) if vlan_tag else 1

    vswitch_address = request.POST.get('vswitch_address')
    vswitch_netmask = request.POST.get('vswitch_netmask')
    pnics = request.POST.getlist('pnics[]')

    ip_address_begin = request.POST.get('ip_address_begin')
    ip_address_end = request.POST.get('ip_address_end')
    dns = request.POST.get('dns')

    host_id = casapi.get_host()['id']

    gateway = request.POST.get('gateway')
    # 判断网关是否存在且唯一
    all_vswitches = casapi.get_all_vswitches(host_id)
    if all_vswitches:
        gateway_list = [v['gateway'] for v in all_vswitches if v['gateway']]
        if gateway_list and gateway:
            res['result'] = 'error'
            res['message'] = u'网关已存在,一台主机只能配置一个网关.'
            return JsonResponse(res)
    else:
        if not gateway:
            res['result'] = 'error'
            res['message'] = u'主机中没有设置网关'
            return JsonResponse(res)

    white_list = white_list.replace(u'，', ',').split(',')
    white_list = ','.join([i.strip() for i in white_list if i])

    if not (npp_name and white_list and vswitch_name):
        res['result'] = 'error'
        res['message'] = u'配置错误,请检查!'
        return JsonResponse(res)

    if int(custom):
        enable_lacp = request.POST.get('enable_lacp', None)

        if len(pnics) > 1 and enable_lacp is None:
            res['result'] = 'error'
            res['message'] = u'链路聚合模式不能为空'
            return JsonResponse(res)

        enable_lacp = 'true' if enable_lacp else 'false'

        if vswitch_address and vswitch_netmask:
            # todo: vSwitch需要注意IP占用的异常
            try:
                # 创建vswitch
                casapi.create_vswitch(name=vswitch_name, description=vswitch_name, hostid=host_id, port_num=32, pnic=pnics,
                                      enable_lacp=enable_lacp, address=vswitch_address, netmask=vswitch_netmask, gateway=gateway)
            except casapi.exceptions.VSwitchAlreadyExist:
                # todo: 更新vswitch
                LOG.info('vSwitch already exists')
                res['result'] = 'error'
                res['message'] = u'vSwitch已经存在'
            except Exception, e:
                LOG.error(str(e))
                res['result'] = 'error'
                res['message'] = u'创建vSwitch失败！请检查设置'

    # 创建network
    if ip_address_begin and ip_address_begin:
        if not vswitch_address:
            vswitch = casapi.get_vswitch_info(host_id, vswitch_name)
            vswitch_address = vswitch['address']
            vswitch_netmask = vswitch['netmask']
            gateway = vswitch['gateway']

        # check arguments
        try:
            address_begin = IP(ip_address_begin)
        except ValueError:
            LOG.exception('Failed to parse the begin address')
            res['result'] = 'error'
            res['message'] = u'起始 IP 地址无法解析'
            return JsonResponse(res)

        try:
            address_end = IP(ip_address_end)
        except ValueError:
            res['result'] = 'error'
            res['message'] = u'结束 IP 地址无法解析'
            return JsonResponse(res)

        try:
            segment1 = address_begin.make_net(vswitch_netmask)
            segment2 = address_end.make_net(vswitch_netmask)
        except ValueError:
            res['result'] = 'error'
            res['message'] = u'子网掩码无法解析'
            return JsonResponse(res)

        if segment1 != segment2:
            res['result'] = 'error'
            res['message'] = u'起始 IP 地址和结束 IP 地址不在同一个子网中'
            return JsonResponse(res)

        if address_begin > address_end:
            res['result'] = 'error'
            res['message'] = u'起始 IP 地址大于结束 IP 地址'
            return JsonResponse(res)

        if gateway:
            try:
                gateway = IP(gateway)
            except ValueError:
                res['result'] = 'error'
                res['message'] = u'网关无法解析'
                return JsonResponse(res)
        else:
            gateway = None

        if dns:
            try:
                dns = IP(dns)
            except ValueError:
                res['result'] = 'error'
                res['message'] = u'DNS无法解析'
                return JsonResponse(res)
        else:
            dns = None

        network = Network.objects.update_or_create(defaults={
            'address_begin': address_begin.strNormal(),
            'address_end': address_end.strNormal(),
            'netmask': segment1.strNetmask(),
            'gateway': gateway and gateway.strNormal(),
            'dns': dns and dns.strNormal()
        }, name='default')[0]

        pairs = {}
        for i in xrange(0, settingsutils.get_desktop_count() + 1):
            tmpaddr = IP(address_begin.int() + i + 1)  # address_begin + 1 for teacher
            if tmpaddr > address_end:
                break
            pairs[random_mac(0x00, MAC_TYPE_VM, i)] = tmpaddr.strNormal()
        dhcputils.config_dhcp_service(
            vswitch_name,
            vlan_tag,
            network.address_begin,
            network.address_end,
            network.netmask,
            network.gateway,
            network.dns,
            pairs,
            'infinite')
        # FIXME
        # if not dhcp:
        #     res['success'] = False
        #     res['msg'] = u'DHCP设置失败'
        #     return JsonResponse(res)

    # 创建网络策略模板
    try:
        casapi.create_profile(npp_name, npp_name, vlan_tag)
    except casapi.exceptions.NppAlreadyExist:
        LOG.info('NPP already exists')
        res['result'] = 'error'
        res['message'] = u'网络策略模板已经存在'
    except Exception, e:
        LOG.error(str(e))
        res['message'] = u'创建网络策略模板失败！请检查设置'
        res['result'] = 'error'

    if acl_name:
        try:
            # 创建acl
            casapi.create_acl(name=acl_name)
        except casapi.exceptions.AclAlreadyExist:
            LOG.info('ACL already exists')
            res['result'] = 'error'
            res['message'] = u'ACL已经存在'
        except Exception, e:
            LOG.error(str(e))
            res['message'] = u'创建ACL失败！请检查设置'
            res['result'] = 'error'

    if res['result'] == 'ok':
        OptsMgr.set_value(VSWITCH_NAME, vswitch_name)
        OptsMgr.set_value(NPP_NAME, npp_name)
        OptsMgr.set_value(VLAN_TAG, vlan_tag)
        OptsMgr.set_value(ACL_NAME, acl_name)
        OptsMgr.set_value(INITIALIZED, True)
        OptsMgr.set_value(ACL_WHITELIST, white_list)
        CasDriver()
        try:
            casapi.refresh_storagepool(host_id, 'isopool')
        except:
            LOG.exception('Failed to refresh isopool')
    return JsonResponse(res)


# 置顶课程
@login_required
@require_POST
def ajax_top_course(request):
    cuuid = request.POST.get("id")
    new_top_count = Course.objects.all().order_by('-priority').first().priority + 1
    try:
        new_top = Course.objects.get(uuid=cuuid)
        new_top.priority = new_top_count
        new_top.save()
    except Course.DoesNotExist:
        LOG.exception('Failed to get course[uuid:%s]' % cuuid)
    return JsonResponse({"result": "ok"})


@require_POST
def ajax_test_cas_connection(request):
    """ 测试cas连接 """
    ret = {}

    if not request.user.is_authenticated():
        return JsonResponse({'authed': False})

    try:
        is_conn = casapi.test_conn()
    except Exception, e:
        LOG.error(str(e))
        if '403' in str(e):
            # 非法访问cas会返回403 Forbidden
            ret['code'] = 403
        is_conn = False
    ret['is_conn'] = is_conn
    ret['authed'] = True
    return JsonResponse(ret)


@login_required
@require_POST
def ajax_refresh_base_image(request):
    """基础镜像刷新"""
    storpool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()
    images = fileutils.get_base_images(storpool)

    paths = [i['path'] for i in images]
    BaseImage.objects.exclude(image_path__in=paths).delete()
    for i in images:
        try:
            BaseImage.objects.get(image_path=i['path'])
            BaseImage.refname = i['name']
            BaseImage.capacity = i['size']
            BaseImage.image_md5 = i['md5']
        except BaseImage.DoesNotExist:
            BaseImage.objects.create(
                name=i['name'].split('.')[0],
                refname=i['name'],
                capacity=i['size'],
                image_path=i['path'],
                image_md5=i['md5'])
    return JsonResponse({'result': 'ok'})


@login_required
@require_GET
def ajax_get_course_pkgfiles(request):
    storpool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()
    files = fileutils.get_course_pkgfiles(storpool)
    return JsonResponse({'result': files})


@login_required
@require_POST
def ajax_import_course(request):
    pkgfile = request.POST.get("pkg_files")

    msg = fileutils.check_course_pkgfile(pkgfile)
    if msg:
        return JsonResponse({'result': 'error', 'message': msg})

    storpool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()
    meta = fileutils.extract_metadata_json(pkgfile)

    base_file = meta['base_file']
    base_name = meta['base_name']
    base_md5 = meta['base_md5']
    base_path = os.path.join(storpool, base_file)
    try:
        base_image = BaseImage.objects.get(image_path=base_path)
        md5sum = fileutils.md5sum(base_image.image_path)
        if md5sum != base_md5:
            # 存在同路径镜像文件且 MD5 不同
            return JsonResponse({'result': 'error', 'message': u'添加基础镜像失败，当前目录已存在同名基础镜像！'})
        else:
            # 存在同路径镜像文件且 MD5 相同
            LOG.info('We find same base image, ignore the step to import base image.')
    except BaseImage.DoesNotExist:
        # 不存在同路径镜像文件，执行解压操作
        fileutils.extract_image(storpool, pkgfile, base_file)

        base_image_names = BaseImage.objects.values_list('name', flat=True)
        suffix = 1
        while True:
            # 处理同名
            if base_name not in base_image_names:
                break
            base_name = u'{}-{}'.format(base_name, suffix)
            suffix += 1

        capacity = 0
        if isinstance(base_path, unicode):
            base_path = base_path.encode('utf-8')
        with open(base_path, 'rb') as f:
            f.seek(0)
            if f.read(4) == 'QFI\xfb':
                f.seek(24)
                capacity = struct.unpack('>Q', f.read(8))[0] / 1024 / 1024
        try:
            base_image = BaseImage.objects.create(
                name=base_name,
                refname=base_file,
                capacity=capacity,
                image_path=os.path.join(storpool, base_file),
                image_md5=base_md5,
                os_type=meta['os_type'],
                os_version=meta['os_version'],
                published=True,
            )
        except:
            LOG.exception('Failed to create base image')
            try:
                os.unlink(base_path)
            except:
                pass
            return JsonResponse({'result': 'error', 'message': u'添加基础镜像失败！'})

    course_file = meta['course_file']
    course_name = meta['course_name']
    course_md5 = meta['course_md5']
    course_path = os.path.join(storpool, course_file)
    try:
        CourseImage.objects.get(image_path=course_path)
        return JsonResponse({'result': 'error', 'message': u'添加课程镜像失败，当前目录已存在同名课程镜像！'})
    except CourseImage.DoesNotExist:
        pass
    fileutils.extract_image(storpool, pkgfile, course_file)
    course_image = CourseImage.objects.create(
        parent=base_image,
        name=course_file,
        capacity=base_image.capacity,
        image_path=os.path.join(storpool, course_file),
        image_md5=course_md5
    )

    host = Host.objects.last()
    vsid = OptsMgr.get_value(VSWITCH_ID)
    vsname = OptsMgr.get_value(VSWITCH_NAME)
    npp_info = casapi.get_npp_info(OptsMgr.get_value(NPP_NAME))
    hpid = casapi.get_hostpool()[u'id']

    course_image_names = Course.objects.values_list('name', flat=True)
    suffix = 1
    while True:
        # 处理同名
        if course_name not in course_image_names:
            break
        course_name = u'{}-{}'.format(course_name, suffix)
        suffix += 1

    profile = CourseProfile.objects.first()
    try:
        course = Course.objects.create(
            name=course_name,
            refname=course_file,
            desc='',
            profile=profile,
            image=course_image,
            visibility=1,
        )
        msg = VirtDriver.instance().add_course(
                hpid, host.uuid, course_file, course_image.image_path, '', profile.cpu, 1,
                profile.memory, base_image.os_type, base_image.get_os_version_display(), '',
                vsid, vsname, npp_info['id'], 'none')
        if msg:
            VirtDriver.instance().get_vm_id(msg["msgId"], course)
    except:
        LOG.exception(u'Failed to create course {}'.format(course_name))
        return JsonResponse({'result': 'error', 'message': u'添加课程镜像失败！'})

    try:
        if isinstance(pkgfile, unicode):
            pkgfile = pkgfile.encode('utf-8')
        os.unlink(pkgfile)
    except:
        LOG.exception(u'Failed to delete {}'.format(pkgfile))

    return JsonResponse({'result': 'ok', 'course': course.name})


@login_required
@require_POST
def ajax_copy_base_image(request):
    """ 复制基础镜像 """
    image_id = request.POST.get('image_id')
    image = BaseImage.objects.get(id=image_id)

    src = image.image_path
    storage_pool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()

    # 获取唯一的base名称
    base_names = BaseImage.objects.values_list('name', flat=True)
    i = 0
    while True:
        name_copy = u'{}_copy_{}'.format(image.name, i)
        if not name_copy in base_names:
            break
        i += 1

    target_name = u'{}.base'.format(uuid.uuid1())
    target = u"{}/{}".format(storage_pool, target_name)
    cp(src, target)

    # 创建虚机
    host = Host.objects.last()
    vsid = OptsMgr.get_value(VSWITCH_ID)
    vsname = OptsMgr.get_value(VSWITCH_NAME)
    npp_info = casapi.get_npp_info(OptsMgr.get_value(NPP_NAME))
    hp_id = casapi.get_hostpool()[u'id']

    msg = casapi.create_vm(host.uuid, hp_id, target_name, name_copy, 2048, 2, 1, image.os_type,
                           image.get_os_version_display(), target, vsid,
                           vsname, npp_info['id'], target, 'none')
    if msg['msgId']:
        LOG.debug('msg={}'.format(msg))
        vm_id = VirtDriver.instance().get_base_image_vm_id(msg['msgId'])

        BaseImage.objects.create(name=name_copy,
                                 refname=target_name,
                                 capacity=image.capacity,
                                 image_path=target,
                                 image_md5=image.image_md5,
                                 os_type=image.os_type,
                                 os_version=image.os_version,
                                 published=False,
                                 extras=BaseImageExtras(vm_id=vm_id))
    else:
        rm(target_name)
    return JsonResponse({"result": "ok"})


@login_required
@require_POST
def ajax_edit_image_name(request):
    """ 编辑镜像名称 """
    image_id = request.POST.get('image_id')
    name = request.POST.get('name')

    form = EditBaseImageNameForm(image_id=image_id, data={'name': name})
    if form.is_valid():
        form.save()
        return JsonResponse({'result': 'ok'})
    else:
        print form.errors
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({'result': 'error', 'message': message})


@login_required
@require_POST
def ajax_copy_course(request):
    """ 复制基础镜像 """
    course_id = request.POST.get('course_id')

    if courseutils.is_in_class(course_id):
        return JsonResponse({'result': 'error', 'message': u'当前课程正在上课,不能复制!'})

    course = Course.objects.get(id=course_id)
    base_image = course.image.parent
    profile = course.profile

    storage_pool = six.itervalues(settings.DEFAULT_STORAGE_POOL).next()

    # 获取不重复的名字
    course_names = Course.objects.values_list('name', flat=True)
    i = 0
    while True:
        name_copy = u'{}_copy_{}'.format(course.name, i)
        if not name_copy in course_names:
            break
        i += 1

    # 课程镜像名称及路径
    target_name = u'{}.course'.format(uuid.uuid1())
    target = u"{}/{}".format(storage_pool, target_name)

    cp(course.image.image_path, target)

    # 创建课程镜像
    course_image = CourseImage.objects.create(
        parent=base_image,
        name=target_name,
        capacity=base_image.capacity,
        image_path=target
    )

    host = Host.objects.last()
    vsid = OptsMgr.get_value(VSWITCH_ID)
    vsname = OptsMgr.get_value(VSWITCH_NAME)
    npp_info = casapi.get_npp_info(OptsMgr.get_value(NPP_NAME))
    hpid = casapi.get_hostpool()[u'id']

    msg = VirtDriver.instance().add_course(
            hpid, host.uuid, target_name, target, course.desc, profile.cpu, 1, profile.memory,
            base_image.os_type, base_image.get_os_version_display(), '',
            vsid, vsname, npp_info['id'], 'none')

    if msg:
        course = Course.objects.create(
            name=name_copy,
            refname=target_name,
            desc=course.desc,
            profile=course.profile,
            image=course_image,
            visibility=1
        )
        VirtDriver.instance().get_vm_id(msg["msgId"], course)
    else:
        rm(target)
    return JsonResponse({"result": "ok"})


@login_required
@require_POST
def ajax_ppt_screenshot(request):
    filename = request.POST.get("filename")
    number = request.POST.get("number")
    fullpath = os.path.join("/opt/doc/public/ppt", filename, str(number)+".png")
    with open(fullpath, 'rb') as f:
        return JsonResponse({"base64": base64.b64encode(f.read())})

@login_required
def grade_list(request):
    Grade = GradeForm()
    Grade_Edit = GradeEditForm()
    grades = Gradeclass.objects.all()
    for item in grades:
        students = Student.objects.filter(grade=item)
        item.totals = len(students) if students else 0
        item.save()
    grade = Gradeclass.objects.all()
    return render(request, 'cloudclass/gradelist.html', {"gradeclass": grade, "Grade": Grade, "Grade_Edit": Grade_Edit})

@login_required
def student_list(request):
    form = StudentForm()
    form_edit = StudentEditForm()
    form_password = ChangeStudentPassword()
    id = request.GET.get("id")
    grade = Gradeclass.objects.all()
    if not id:
        if not grade:
            topics = pagination_student(request, "")
            return render(request, 'cloudclass/studentlist.html', {"students": topics, "gradeclass": grade,
            "grade_id": "0", "form": form, "form_edit": form_edit, "form_password": form_password, filter: ""})
        id = grade[0].id
    name = request.GET.get("name")
    num = request.GET.get("num")
    card = request.GET.get("card")
    q = None
    key = ""
    if name:
        key = "&name=%s" % name
        q = Q(name__startswith=name)
    if num:
        key += "&num=%s" % num
        q = q & Q(num__startswith=num) if q else Q(num__startswith=num)
    if card:
        key += "&card=%s" % card
        q = q & Q(idcard__startswith=card) if q else Q(idcard__startswith=card)
    if q:
        students = Student.objects.filter(grade_id=id).filter(q)
    else:
        students = Student.objects.filter(grade_id=id)
    topics = pagination_student(request, students)
    return render(request, 'cloudclass/studentlist.html', {"students": topics, "gradeclass": grade,
        "grade_id": id, "form": form, "form_edit": form_edit, "form_password": form_password, "filter": key})


def pagination_student(request, students):
    limit = request.GET.get("limit")
    limit = limit if limit else 10
    paginator = Paginator(students, limit)
    page = request.GET.get('page')
    try:
        topics = paginator.page(page)
    except PageNotAnInteger:
        topics = paginator.page(1)
    except EmptyPage:
        topics = paginator.page(paginator.num_pages)
    return topics

@login_required
@require_POST
def import_student_list(request):
    """导入学生列表"""
    failed = 0 #导入失败的学生数量
    totals = 0 #学生数量
    path = request.POST.get("path")
    class_id = request.POST.get("id")
    if not path or not os.path.exists(path):
        return JsonResponse({"code": -1, "message": u"请先上传csv文件!"})
    with open(r'%s' % path, 'r') as f:
        text = csv.reader(f)
        students = list(text)
        if students:
            students.pop(0)
            totals = len(students)
        else:
            return JsonResponse({"code": -1, "message": u"学生列表为空!"})
        for student in students:
            result = check_format_csv(student)
            if result.get("code") == 200:
                student = result.get("student")
                s = Student()
                s.save(student, class_id)
            else:
                failed += 1
    os.remove(path)#csv删除文件
    stu = Student.objects.filter(grade_id=class_id)
    student_list = [{"id": item.id, "name": item.name, "num": item.num, "password": item.password, "idcard": item.idcard,
                     "gender": item.gender, "vm_num": item.stu_vm_number} for item in stu]
    if failed == 0:
        return JsonResponse({"code": 1, "students": student_list})
    else:
        return JsonResponse({"code": -2, "students": student_list, "failed": failed, "totals": totals})


def check_format_csv(student):
    length = len(student)
    if length != 6:
        return {"code": 1001, "message": u"导入文件数据列数不对"}
    num = student[1]
    res_num = re.match("(^\d\.\d+(E|e)\d$)|^\d+$", num)
    num_length = len(num)
    if num_length > 10:
        return {"code": 1002, "message": u"学号超过10位"}
    if not res_num:
        return {"code": 1003, "message": u"学号包含数字以外的字符"}
    password = unicode(student[2], 'gb2312')
    pattern = re.compile(u'[\u4e00-\u9fa5]+')
    match = pattern.search(password)
    if match:
        return {"code": 1004, "message": u"密码格式不正确"}
    card = student[3]
    res_card = re.match("^\d+$", card)
    if not res_card:
        return {"code": 1005, "message": u"一卡通卡号含数字以外的字符"}
    if len(card) > 20:
        return {"code": 1006, "message": u"一卡通卡号超过20位"}
    vm_num = student[5]
    res_vm_num = re.match("^\d+$", vm_num)
    if not res_vm_num:
        return {"code": 1007, "message": u"学生机编号含数字以外的字符"}
    if len(vm_num) > 3:
        return {"code": 1008, "message": u"学生机编号含数字以外的字符"}
    try:
        Student.objects.get(num=student[1])
        return {"code": 1009, "message": u"该学号已经存在"}
    except Exception, e:
        print u"学号:", e.message
    try:
        Student.objects.get(stu_vm_number=student[5])
        return {"code": 1009, "message": u"该一卡通卡号已经存在"}
    except Exception, e:
        print u"一卡通卡号:", e.message
    name = unicode(student[0], 'gb2312')
    student[0] = name.encode("utf8")
    student[1] = str(int(float(num)))
    student[3] = str(int(float(card)))
    student.insert(5, "")
    if student[4].decode("gbk") == u"男":
        student[4] = 1
    else:
        student[4] = 0
    return {"code": 200, "message": "ok", "student": student}


@login_required
@require_POST
def ajax_add_student(request):
    """添加学生账号"""
    form = StudentForm(request.POST)
    if form.is_valid():
        result = form.save()
        return JsonResponse(result)
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({"code": -1, "message": message})


@login_required
@require_POST
def ajax_update_student(request):
    """修改学生账号"""
    form = StudentEditForm(request.POST)
    if form.is_valid():
        result = form.save()
        return JsonResponse(result)
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({"code": -1, "message": message})

@login_required
@require_POST
def ajax_delete_student(request):
    """删除学生账号"""
    id = json.loads(request.POST.get("id"))
    id = id if type(id) == list else [id]
    for item in id:
        Student.objects.get(id=item).delete()
    return JsonResponse({"code": 1, "message": "ok"})

@login_required
@require_POST
def ajax_update_password(request):
    """修改学生账号密码"""
    form = ChangeStudentPassword(request.POST)
    if form.is_valid():
        result = form.save()
        return JsonResponse(result)
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({"code": -1, "message": message})

@login_required
@require_POST
def ajax_get_student(request):
    """获取学生信息"""
    id = request.POST.get("id")
    s = Student.objects.get(id=id)
    student = {}
    student["id"] = s.id
    student["name"] = s.name
    student["num"] = s.num
    student["idcard"] = s.idcard
    student["gender"] = s.gender
    student["grade_id"] = s.grade_id
    student["vm_num"] = s.stu_vm_number
    return JsonResponse({"code": 1, "message": student})

@login_required
@require_POST
def ajax_add_gradeclass(request):
    """添加班级"""
    form = GradeForm(request.POST)
    if form.is_valid():
        result = form.save()
        return JsonResponse(result)
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({"code": -1, "message": message})

@login_required
@require_POST
def ajax_delete_gradeclass(request):
    """删除班级"""
    grade_id = json.loads(request.POST.get("id"))
    grade_id = grade_id if type(grade_id) == list else [grade_id]
    for id in grade_id:
        Gradeclass.objects.get(id=id).delete()
        students = Student.objects.filter(grade_id=id)
        for item in students:
            item.delete()
    return JsonResponse({"code": 1, "message": "ok"})

@login_required
@require_POST
def ajax_get_gradeclass(request):
    """获取班级信息"""
    id = request.POST.get("id")
    g = Gradeclass.objects.get(id=id)
    gradeinfo = {"name": g.name, "desc": g.description, "totals": g.totals}
    return JsonResponse({"code": 1, "message": gradeinfo})

@login_required
@require_POST
def ajax_update_gradeclass(request):
    """修改班级信息"""
    form = GradeEditForm(request.POST)
    if form.is_valid():
        result = form.save()
        return JsonResponse(result)
    else:
        errors = form.errors
        message = form_error_msg(errors)
        return JsonResponse({"code": -1, "message": message})

@login_required
@require_POST
@csrf_exempt
def ajax_upload_csv(request):
    file = request.FILES.get("Filedata", None)
    if file:
        file_name = "students.csv"
        path = os.path.join(settings.MEDIA_ROOT, file_name)
        fp = open(path, 'wb')
        for content in file.chunks():
            fp.write(content)
        fp.close()
        return JsonResponse({"code": 1, "message": path})
    else:
        return JsonResponse({"code": -1, "message": "upload falied!"})

@csrf_exempt
def export_students_csv(request):
    id = request.GET.get("id")
    filename = ""
    try:
        g = Gradeclass.objects.get(id=id)
        filename = g.name
        students = [[item.name.encode("gb2312"), item.num, item.password, item.idcard, u"女".encode("gb2312") if item.gender == 0 else u"男".encode("gb2312"),
                     item.stu_vm_number] for item in Student.objects.filter(grade_id=id)]
    except Exception, e:
        return JsonResponse({"code": -1, "message": e.message})
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename.encode("utf8")
    writer = csv.writer(response)
    writer.writerow([u'姓名'.encode("gb2312"), u"学号".encode("gb2312"), u"密码".encode("gb2312"),
    u"一卡通卡号".encode("gb2312"), u"性别".encode("gb2312"), u"学生机编号".encode("gb2312")])
    for item in students:
        writer.writerow(item)
    return response



