# -*- coding: utf-8 -*-
import json
import logging
import os
import shutil
import hmac
import binascii
import hashlib

from django.conf import settings
from django.db import OperationalError
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseBadRequest
from django.utils import six
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
import re
from cloudapi.casapi.exceptions import VmDoesNotExist

from cloudapi.driver import VirtDriver
from common.models import Course, Classroom, Network, Desktop, Terminal, Gradeclass, Student
from utils import cacheutils
from utils import settingsutils
from utils.httputils import HttpResponseNoContent, JsonResponseNotFound, \
    HttpResponseConflict, JsonResponseServerError, \
    JsonResponseBadRequest, license_required, authenticate_required, fmt_error, JsonResponseConflict
from utils.typeutils import FixedSizeContainer
from utils.settingsutils import OptsMgr, TERMINAL_NUMBERS

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout

LOG = logging.getLogger(__name__)


# Create your views here.
@license_required
@require_GET
@csrf_exempt
def get_courses(request):
    """获取课程列表。访问对象：教师端、移动端和瘦终端。"""
    classroom = cacheutils.get_classroom()
    LOG.debug('Classroom = %s' % classroom)
    if classroom is None:
        LOG.error('No classroom matches the given query.')
        return JsonResponseNotFound({'message': 'No classroom matches the given query.'})

    courses = Course.objects.exclude(visibility=0).order_by('-priority')
    LOG.debug("course = %s" % courses)
    cs = [{'uuid': x.uuid, 'name': x.name, 'desc': x.desc, 'os_type': x.os_type, 'os_version': x.os_version,
           'state': classroom.state if classroom.course_id and classroom.course.pk == x.pk else Classroom.ST_NORMAL}
          for x in courses]
    return JsonResponse({'courses': cs})


@license_required
@authenticate_required
@require_GET
@csrf_exempt
def current_course(request):
    classroom = cacheutils.get_classroom()
    LOG.debug('Classroom = %s' % classroom)
    if classroom is None:
        LOG.error('No classroom matches the given query.')
        return JsonResponseNotFound({'message': 'No classroom matches the given query.'})

    if classroom.state != Classroom.ST_NORMAL:
        course = classroom.course
        cs = {'uuid': course.uuid, 'name': course.name, 'desc': course.desc, 'os_type': course.os_type,
              'os_version': course.os_version, 'state': classroom.state}
        return JsonResponse({'currentCourse': cs})
    else:
        return JsonResponse({'currentCourse': ''})


@license_required
@authenticate_required
@require_POST
@csrf_exempt
def begin_course(request):
    """执行上课。访问对象：教师端。"""
    cuuid = request.POST.get('uuid')

    classroom = cacheutils.get_classroom()
    if classroom is None:
        LOG.error('No classroom matches the given query.')
        return JsonResponseNotFound({'message': 'No classroom matches the given query.'})

    if classroom.state != Classroom.ST_NORMAL:
        return JsonResponseConflict(fmt_error(4092, u'不允许再次上课。'))

    course = cacheutils.get_course(cuuid)
    if course is None:
        LOG.error('No course matches the given query.')
        return JsonResponseNotFound({'message': 'No course matches the given query.'})
    if course.visibility == 0:
        LOG.error('No course can used by current user.')
        return JsonResponseNotFound({'message': 'No course can used by current user.'})
    try:
        network = Network.objects.get(name='default')
    except Network.DoesNotExist:
        LOG.error('No network matches the given query.')
        return JsonResponseNotFound({
            'message': 'No %s matches the given query.' % Network._meta.object_name})

    prefix = settings.DEFAULT_DESKTOP_PREFIX
    count = settingsutils.get_desktop_count1(course.profile.cpu, course.profile.memory)

    if request.user.is_superuser or request.user.is_staff:
        # 准备上课
        classroom.state = classroom.ST_PRE_CLASS
        classroom.course = course
        classroom.save()
        cacheutils.clear_classroom(classroom.name)
    VirtDriver.instance().begin_course(classroom.host, course, network, prefix, count)
    if request.user.is_superuser or request.user.is_staff:
        classroom.state = classroom.ST_ON_CLASS
        try:
            classroom.save()
        except OperationalError:
            LOG.exception('Failed to save classroom state')
            try:
                from django.db import close_old_connections
                close_old_connections()
                classroom.save()
            except:
                LOG.exception('Failed to retry to save classroom state')
        cacheutils.clear_classroom(classroom.name)

    return HttpResponseNoContent()


@license_required
@authenticate_required
@require_POST
@csrf_exempt
def create_teacher_desktop(request):
    cuuid = request.POST.get('uuid')
    course = cacheutils.get_course(cuuid)
    if course is None:
        LOG.error('No course matches the given query.')
        return JsonResponseNotFound({'message': 'No course matches the given query.'})
    classroom = cacheutils.get_classroom()
    if classroom is None:
        LOG.error('No classroom matches the given query.')
        return JsonResponseNotFound({'message': 'No classroom matches the given query.'})
    if classroom.state != Classroom.ST_ON_CLASS:
        return HttpResponseConflict()
    try:
        network = Network.objects.get(name='default')
    except Network.DoesNotExist:
        LOG.exception('No %s matches the given query.' % Network._meta.object_name)
        return JsonResponseNotFound({
            'message': 'No %s matches the given query.' % Network._meta.object_name})
    tn_id = 0
    hostname = _get_hostname(tn_id)
    desktops = Desktop.objects.filter(~Q(course=course), name=hostname)
    VirtDriver.instance().delete_desktops(desktops)
    try:
        desktop = Desktop.objects.get(course=course, name=hostname)
        LOG.debug("desktop info , desktop = %s " % desktop)
        VirtDriver.instance().power_on_vm(desktop.uuid)
    except Desktop.DoesNotExist:
        if not VirtDriver.instance().free_course(classroom.host, course, network, tn_id, hostname):
            return JsonResponseServerError({
                'message': 'Failed to create instance %s of course %s' % (hostname, course.name)})
    return HttpResponseNoContent()


@license_required
@require_POST
@csrf_exempt
def free_course(request):
    """执行自由上课。访问对象：瘦终端。"""
    cuuid = request.POST.get('uuid')
    terminal_mac = request.POST.get("mac")
    terminal_ip = request.POST.get("ip")
    terminal_name = request.POST.get("name")
    LOG.debug("post = {'course_uuid': '%s',  'terminal_mac': '%s', 'terminal_ip': '%s', 'terminal_name': '%s' }" %
              (cuuid, terminal_mac, terminal_ip, terminal_name))

    classroom = cacheutils.get_classroom()
    LOG.debug('classroom = %s' % classroom)
    if classroom is None:
        LOG.error('No classroom matches the given query.')
        return JsonResponseNotFound({'message': 'No classroom matches the given query.'})
    if classroom.state != classroom.ST_NORMAL:  # 提示正在上课
        return HttpResponseForbidden()

    course = cacheutils.get_course(cuuid)
    if course is None:
        LOG.error('No course matches the given query.')
        return JsonResponseNotFound({'message': 'No course matches the given query.'})
    try:
        network = Network.objects.get(name='default')
        LOG.debug("network = %s" % network)
    except Network.DoesNotExist:
        LOG.exception('No %s matches the given query.' % Network._meta.object_name)
        return JsonResponseNotFound({
            'message': 'No %s matches the given query.' % Network._meta.object_name})

    tn_id = _update_terminal_info(terminal_name, terminal_mac, terminal_ip)[0]
    if tn_id == -1:
        # 没有空位
        return HttpResponseNotFound()
    hostname = _get_hostname(tn_id)
    desktops = Desktop.objects.filter(~Q(course=course), name=hostname)
    LOG.debug("desktops = %s" % desktops)
    VirtDriver.instance().delete_desktops(desktops)
    try:
        desktop = Desktop.objects.get(course=course, name=hostname)
        LOG.debug("desktop info , desktop = %s " % desktop)
        VirtDriver.instance().power_on_vm(desktop.uuid)
    except Desktop.DoesNotExist:
        if not VirtDriver.instance().free_course(classroom.host, course, network, tn_id, hostname):
            return JsonResponseServerError({
                'message': 'Failed to create instance %s of course %s' % (hostname, course.name)})
    return HttpResponseNoContent()


@license_required
@authenticate_required
@require_POST
@csrf_exempt
def finish_course(request):
    """执行下课。访问对象：教师端。"""
    # TODO finish course by classroom id
    cuuid = request.POST.get('uuid')

    classroom = cacheutils.get_classroom()
    if classroom is None:
        LOG.error('No classroom matches the given query.')
        return JsonResponseNotFound({'message': 'No classroom matches the given query.'})

    course = cacheutils.get_course(cuuid)
    if course is None:
        LOG.error('No course matches the given query.')
        return JsonResponseNotFound({'message': 'No course matches the given query.'})
    desktops = Desktop.objects.filter(course=course)

    if request.user.is_superuser or request.user.is_staff:
        # 准备下课
        classroom.state = Classroom.ST_POST_CLASS
        classroom.save()
        cacheutils.clear_classroom(classroom.name)
    VirtDriver.instance().delete_desktops(desktops)
    VirtDriver.instance().delete_desktops_ex(classroom.host)
    if request.user.is_superuser or request.user.is_staff:
        # 恢复课程初始状态
        classroom.state = Classroom.ST_NORMAL
        classroom.course = None
        classroom.save()
        cacheutils.clear_classroom(classroom.name)

    return JsonResponse({'result': '0'})


def _update_terminal_info(tname, tmac, tip):
    tmac = conv_mac_addr(tmac)
    # FIXME 暂不考虑瘦客户机MAC地址回收，即id是连续递增的
    tns = cacheutils.get_tns()
    try:
        tn_id = tns.index(tmac)
    except ValueError:
        tn_id = tns.append(tmac)
        if tn_id != -1:
            OptsMgr.set_value(TERMINAL_NUMBERS, tns)
            cacheutils.clear_tns()

    # 记录终端
    terminal = cacheutils.get_or_create_terminal(tmac, tname, tip)
    modified = False
    if tip != terminal.ip_address:
        terminal.ip_address = tip  # 更新瘦客户机IP地址
        modified = True
    if tname != terminal.name:
        terminal.name = tname  # 更新瘦客户机名称
        modified = True
    if modified:
        terminal.save()
        cacheutils.clear_terminal(tmac)

    return tn_id, terminal


def _get_hostname(terminal_number_id):
    prefix_name = settings.DEFAULT_DESKTOP_PREFIX
    hostname = VirtDriver.instance().generate_hostname(prefix_name, terminal_number_id)
    return hostname


@license_required
@require_GET
@csrf_exempt
def get_visitor(request):  # no authenticate required for terminals
    """获取虚拟机的信息。访问对象：瘦终端。"""
    course_uuid = request.GET.get('uuid')
    course = cacheutils.get_course(course_uuid)
    if course is None:
        LOG.warning('Not found course[uuid:%s].' % course_uuid)
        return JsonResponseNotFound(fmt_error(4044, u'课程 uuid = {}'.format(course_uuid)))

    if request.user.is_authenticated():
        tn_id = 0
        hostname = _get_hostname(tn_id)
        desktop = cacheutils.get_desktop(course, hostname)
        if desktop is None:
            # 没有桌面可以连接
            return JsonResponseNotFound(fmt_error(4045, u'教师云桌面不存在，请先创建教师云桌面！'))
    else:
        terminal_ip = request.GET.get('ip')
        terminal_name = request.GET.get('name')
        terminal_mac = request.GET.get('mac')
        tn_id = _update_terminal_info(terminal_name, terminal_mac, terminal_ip)[0]
        if tn_id == -1:
            # 没有空位
            return JsonResponseBadRequest(fmt_error(4000, u'可连接瘦终端已经达到上限。'))
        hostname = _get_hostname(tn_id)
        desktop = cacheutils.get_desktop(course, hostname)
        if desktop is None:
            classroom = cacheutils.get_classroom()
            if classroom.state == Classroom.ST_PRE_CLASS:
                # 桌面还没准备好
                return HttpResponseConflict()
            else:
                # 没有桌面可以连接
                return JsonResponseNotFound(fmt_error(4045, u'云桌面不存在，出现异常。'))

    visitor = {
        # old required fields
        'ipaddr': desktop.ip_address,
        'port': desktop.port1 if desktop.port1 == 3389 else desktop.port2,
        'auth_type': desktop.get_protocol1_display() if desktop.port1 == 3389 else desktop.get_protocol2_display(),
        'username': desktop.username1,
        'password': desktop.password1,
        'hostname': desktop.name,
        # both required fields
        'uuid': desktop.uuid,
        # new required fields
        'name': desktop.name,
        'ip_address': desktop.ip_address,
        'protocol1': desktop.get_protocol1_display(),
        'address1': desktop.address1,
        'port1': desktop.port1,
        'username1': desktop.username1,
        'password1': desktop.password1,
        'protocol2': desktop.get_protocol2_display(),
        'address2': desktop.address2,
        'port2': desktop.port2,
        'username2': desktop.username2,
        'password2': desktop.password2
    }

    return JsonResponse(visitor)


@require_POST
@csrf_exempt
def ajax_teacher_login(request):
    username = request.POST.get("username")
    password = request.POST.get("password")
    auto_login = request.POST.get('autologin')
    LOG.debug("Username=%s, Password=%s" % (username, password))

    if username is None and password is None:
        username = request.POST.get('name')
        password = request.POST.get('pwd')

    user = authenticate(username=username, password=password)

    if user is None:
        msg = {'result': 'invalid_login'}
    elif not user.is_active:
        msg = {'result': 'inactive'}
    else:
        if auto_login:
            request.session.set_expiry(7 * 24 * 60 * 60)
        else:
            request.session.set_expiry(0)
        auth_login(request, user)
        msg = {
            'result': 'ok',
            'is_admin': user.is_superuser,
        }
    return JsonResponse(msg)


@license_required
@authenticate_required
@require_POST
@csrf_exempt
def ajax_teacher_logout(request):
    auth_logout(request)
    return HttpResponseNoContent()


@require_GET
@csrf_exempt
def get_mac_address_mapping(request):
    tmac = request.GET.get('tmac')
    vmac = request.GET.get('vmac')

    tns = cacheutils.get_tns()
    if tmac:
        tmac = conv_mac_addr(tmac)
        vmac = None
        try:
            tn_id = tns.index(tmac)
            desktops = Desktop.objects.all()
            for desktop in desktops:
                _, index = desktop.name.rsplit('_', 1)
                if tn_id == int(index):
                    vmac = desktop.mac_address
                    break
        except ValueError:
            LOG.warning('Failed to index terminal %s' % tmac)
        data = {'vmac': vmac, 'tmac': tmac}
    elif vmac:
        try:
            desktop = Desktop.objects.get(mac_address=vmac)
            _, index = desktop.name.rsplit('_', 1)
            tmac = tns[int(index)]
        except Desktop.DoesNotExist:
            pass
        except IndexError:
            pass
        data = {'vmac': vmac, 'tmac': tmac}
    else:
        data = []
        desktops = Desktop.objects.all()
        for desktop in desktops:
            _, index = desktop.name.rsplit('_', 1)
            try:
                terminal_mac_address = tns[int(index)]
            except IndexError:
                terminal_mac_address = None
            d = {
                'vmac': desktop.mac_address,
                'tmac': terminal_mac_address,
            }
            data.append(d)
    return JsonResponse(data, safe=False)


@license_required
@require_POST
@csrf_exempt
def revert_desktop(request):
    """还原虚拟机。访问对象：教师端。"""
    classroom = cacheutils.get_classroom()
    LOG.debug('classroom = %s' % classroom)
    if classroom is None:
        LOG.error('No classroom matches the given query.')
        return JsonResponseNotFound({'message': 'No classroom matches the given query.'})

    if request.user.is_authenticated():
        tn_id = 0
    else:
        tmac = request.POST.get('tmac')
        if not tmac:
            return HttpResponseBadRequest()

        tmac = conv_mac_addr(tmac)
        tns = cacheutils.get_tns()
        try:
            tn_id = tns.index(tmac)
        except IndexError:
            return JsonResponseNotFound({'message': 'Not found the seat of %s.' % tmac})

    desktops = Desktop.objects.all()
    for d in desktops:
        _, index = d.name.rsplit('_', 1)
        if int(index) == tn_id:
            VirtDriver.instance().revert_desktop(classroom.host, d)
            break
    else:
        return JsonResponseNotFound({
            'message': 'No %s matches the given query.' % Desktop._meta.object_name})

    return HttpResponseNoContent()


@license_required
@authenticate_required
@require_GET
@csrf_exempt
def get_network_state(request):
    """获取禁网状态。访问对象：教师端。"""
    try:
        network = Network.objects.get(name='default')
    except Network.DoesNotExist:
        LOG.exception('No %s matches the given query.' % Network._meta.object_name)
        return JsonResponseNotFound({
            'message': 'No %s matches the given query.' % Network._meta.object_name})

    action = 'OPEN' if network.activate_external else 'CLOSE'
    return JsonResponse({'external': action})


@license_required
@authenticate_required
@require_POST
@csrf_exempt
def control_desktop_network(request):
    """是否禁网。访问对象：教师端。"""
    action = request.POST.get('action')
    if action not in ('OPEN', 'CLOSE'):
        return JsonResponseBadRequest({
            'message': 'action should be "OPEN" or "CLOSE"'})
    try:
        network = Network.objects.get(name='default')
    except Network.DoesNotExist:
        LOG.exception('No %s matches the given query.' % Network._meta.object_name)
        return JsonResponseNotFound({
            'message': 'No %s matches the given query.' % Network._meta.object_name})
    VirtDriver.instance().set_activate_external_network(action)
    network.activate_external = action == 'OPEN'
    network.save()
    return JsonResponse({'external': action})


@license_required
@require_POST
@csrf_exempt
def control_desktop_power(request):
    """控制虚拟机电源。访问对象：教师端。"""
    desktop_uuid = request.POST.get('desktop_uuid')
    action = request.POST.get('action')
    if action not in ('REBOOT', 'POWERON', 'POWEROFF'):
        return JsonResponseBadRequest({
            'message': 'action should be "REBOOT", "POWERON" or "POWEROFF"'})
    try:
        desktop = Desktop.objects.get(uuid=desktop_uuid)
        host = request.get_host().split(':')[0]
    except Desktop.DoesNotExist:
        return JsonResponseNotFound({'message': 'desktop with uuid %s does not found!' % desktop_uuid})

    if action == 'POWERON':
        VirtDriver.instance().poweron(host, desktop)
    elif action == 'POWEROFF':
        VirtDriver.instance().power_off_vm(desktop_uuid)
    else:
        VirtDriver.instance().reboot(host, desktop)
    return HttpResponseNoContent()


@license_required
@authenticate_required
@require_GET
@csrf_exempt
def get_terminal_list(request):
    """获取瘦终端列表。访问对象：教师端。"""
    tns = cacheutils.get_tns()

    terminals = Terminal.objects.all()
    d1 = {}
    for idx, tmac in enumerate(tns, 1):
        if tmac:
            try:
                terminal = terminals.get(mac_address=tmac)
                d1[idx] = {
                    'tmac': terminal.mac_address,
                    'tip': terminal.ip_address,
                    'tname': terminal.name,
                }
            except Terminal.DoesNotExist:
                pass

    desktops = Desktop.objects.all()
    d2 = {}
    for desktop in desktops:
        idx = int(desktop.name.rsplit('_', 1)[1])
        d2[idx] = {
            'vmac': desktop.mac_address,
            'vuuid': desktop.uuid,
        }
    data = [dict(d1[k].items() + (d2[k].items() if k in d2 else [('vuuid', None), ('vmac', None)])) for k in d1]
    return JsonResponse({'terminals': data})


@license_required
@authenticate_required
@require_POST
@csrf_exempt
def poweroff(request):
    """关闭服务器。访问对象：教师端。"""
    return HttpResponseNoContent()


def conv_mac_addr(mac1):
    """XXXXXXXXXXXX -> XX:XX:XX:XX:XX:XX"""
    if ':' not in mac1:
        mac2 = ':'.join(a + b for a, b in zip(mac1[::2], mac1[1::2]))
    else:
        mac2 = mac1
    return mac2.upper()


@license_required
@authenticate_required
@require_POST
@csrf_exempt
def sort_terminals(request):
    """上传编号。访问对象：教师端。"""
    tns = request.POST.get('tns')
    try:
        tns = json.loads(tns)
        tns = {int(k): conv_mac_addr(v) for k, v in six.iteritems(tns)}
    except ValueError:
        LOG.exception('Failed to parse json "tns"')
        return JsonResponse({'code': 4000,
                             'message': u'请求参数错误'})

    tn_list = FixedSizeContainer(settingsutils.get_desktop_count())
    for i, v in six.iteritems(tns):
        try:
            tn_list[i] = v
        except IndexError:
            LOG.exception('Failed to put value %s at index %s' % (v, i))

    OptsMgr.set_value(TERMINAL_NUMBERS, tn_list)
    cacheutils.clear_tns()
    return JsonResponse({'code': 0})


@license_required
@authenticate_required
@require_GET
@csrf_exempt
def clean_files(request):
    """Samba 清理文件。访问对象：教师机。"""
    rootdir = settings.WORKSPACEROOT
    PATTERN = re.compile(r'stu_[0-9]+')
    for fname in os.listdir(rootdir):
        fpath = os.path.join(rootdir, fname)
        if PATTERN.match(fname) and os.path.isdir(fpath):
            for i in os.listdir(fpath):
                x = os.path.join(fpath, i)
                if os.path.isdir(x):
                    shutil.rmtree(x, ignore_errors=True)
                else:
                    os.remove(x)
    return JsonResponse({"result": "ok"})


@license_required
@authenticate_required
@require_GET
@csrf_exempt
def get_desktop_count(request):
    return JsonResponse({'desktop_count': int(settingsutils.get_desktop_count())})


@license_required
@require_GET
@csrf_exempt
def get_desktop_state(request):
    # 当前课程
    # 当前云桌面，名称，IP 地址
    # 云桌面电源状态
    classroom = cacheutils.get_classroom()
    if classroom is None:
        LOG.warning('Not found classroom["default"].')
        return JsonResponseNotFound(fmt_error(4041, u'教室 name="default"'))
    if classroom.state == Classroom.ST_PRE_CLASS:
        return HttpResponseConflict()
    elif classroom.state == Classroom.ST_POST_CLASS:
        return JsonResponseBadRequest(fmt_error(4000, u'当前未上课！'))

    tmac = request.GET.get('tmac')
    tns = cacheutils.get_tns()
    try:
        tn_id = tns.index(conv_mac_addr(tmac))
    except ValueError:
        return JsonResponseNotFound(fmt_error(4000, u'可连接瘦终端已经达到上限。'))

    course = classroom.course
    if course:
        count = settingsutils.get_desktop_count1(course.profile.cpu, course.profile.memory)
        if course.profile.cpu == 2 and count > settingsutils.get_max_users():
            count //= 2
        if tn_id > count:
            return JsonResponseNotFound(fmt_error(4000, u'可连接瘦终端已经达到上限。'))
    else:
        course_uuid = request.GET.get('course_uuid')
        course = cacheutils.get_course(course_uuid)
        if course is None:
            LOG.warning('Not found course[uuid:%s].' % course_uuid)
            return JsonResponseNotFound(fmt_error(4044, u'课程 uuid = {}'.format(course_uuid)))

    hostname = _get_hostname(tn_id)
    # 检查虚拟机是否存在
    desktop = cacheutils.get_desktop(course, hostname)
    if desktop is None or not desktop.uuid:
        return JsonResponseNotFound(fmt_error(4045, u'云桌面不存在，出现异常。'))

    try:
        state = VirtDriver.instance().get_vm_status(desktop.uuid)
    except VmDoesNotExist:
        return JsonResponseNotFound(fmt_error(4045, u'云桌面不存在，出现异常。'))

    data = {
        'course_name': course.name,
        'course_id': course.id,
        'desktop_name': desktop.name,
        'desktop_id': desktop.id,
        'desktop_uuid': desktop.uuid,
        'desktop_state': state,
    }
    return JsonResponse(data)


@license_required
@require_POST
@csrf_exempt
def reset_desktop_state(request):
    classroom = cacheutils.get_classroom()
    if classroom is None:
        LOG.warning('Not found classroom["default"].')
        return JsonResponseNotFound(fmt_error(4041, u'教室 name="default"'))
    if classroom.state == Classroom.ST_PRE_CLASS:
        return HttpResponseConflict()
    elif classroom.state == Classroom.ST_POST_CLASS:
        return JsonResponseBadRequest(fmt_error(4000, u'当前未上课！'))

    try:
        network = Network.objects.get(name='default')
    except Network.DoesNotExist:
        return JsonResponseNotFound(fmt_error(4046, u'网络 name="default"'))

    host = classroom.host

    tmac = request.POST.get('tmac')
    tns = cacheutils.get_tns()
    try:
        tn_id = tns.index(conv_mac_addr(tmac))
    except ValueError:
        return JsonResponseNotFound(fmt_error(4000, u'可连接瘦终端已经达到上限。'))

    course = classroom.course
    if course:
        count = settingsutils.get_desktop_count1(course.profile.cpu, course.profile.memory)
        if course.profile.cpu == 2 and count > settingsutils.get_max_users():
            count //= 2
        if tn_id > count:
            return JsonResponseNotFound(fmt_error(4000, u'可连接瘦终端已经达到上限。'))
    else:
        course_uuid = request.GET.get('course_uuid')
        course = cacheutils.get_course(course_uuid)
        if course is None:
            LOG.warning('Not found course[uuid:%s].' % course_uuid)
            return JsonResponseNotFound(fmt_error(4044, u'课程 uuid = {}'.format(course_uuid)))

    hostname = _get_hostname(tn_id)
    # 检查虚拟机是否存在
    desktop = cacheutils.get_desktop(course, hostname)
    if desktop is None:
        # 如果不存在，则创建
        VirtDriver.instance().free_course(host, course, network, tn_id, hostname)
    else:
        # 检查虚拟机是否开机
        if desktop.uuid:
            try:
                # status = VirtDriver.instance().get_vm_status(desktop.uuid)
                # if status in ('shutOff', 'paused'):
                #     if status == 'paused':
                #         VirtDriver.instance().force_power_off_vm(desktop.uuid, wait=True)
                #     # 如果未开机，则开机
                #     VirtDriver.instance().poweron(request.get_host().split(':')[0], desktop)
                # elif status == 'running':
                #     # 如果已经开机，则还原
                #     VirtDriver.instance().revert_desktop(host, desktop)
                VirtDriver.instance().revert_desktop(host, desktop)
            except VmDoesNotExist:
                # 如果不存在，则创建
                VirtDriver.instance().free_course(host, course, network, tn_id, hostname)

    return HttpResponseNoContent()


@license_required
@require_GET
@csrf_exempt
def get_gradeclass(request):
    """获取班级列表"""
    try:
        grade = [{'id': x.id, 'name': x.name, "desc": x.description, "totals": x.totals, "seq": x.seq, "is_init": x.is_init}
                 for x in Gradeclass.objects.all()]
    except Exception, e:
        LOG.error(e.message)
        return JsonResponse({'code': 1, 'message': e.message})
    return JsonResponse({'code': 1, 'grade': grade})

@license_required
@require_GET
@csrf_exempt
def get_studentslist(request):
    """获取学生列表"""
    grade_id = request.GET.get("grade_id")
    try:
        students = [{'id': x.id, 'name': x.name, "password": x.password, "num": x.num, "idcard": x.idcard, "gender": x.gender,
                 "vm_number": x.stu_vm_number} for x in Student.objects.filter(grade_id=grade_id)]
    except Exception, e:
        LOG.error(e.message)
        return JsonResponse({'code': 1, 'message': e.message})
    return JsonResponse({'code': 1, 'students': students})

@license_required
@require_POST
@csrf_exempt
def assign_to_student(request):
    #todo 自动分配策略
    info = request.POST.get("tns")
    dic = json.loads(info)
    strategory = dic.get("type")
    vm_nums = dic.get("vm_nums")
    sum = Student.objects.all().count()
    if strategory == '1':
        for x in Student.objects.all():
            x.stu_vm_number = x.num
            x.save()
    else:#todo 手动分配策略
        vm_nums = vm_nums
        if not vm_nums:
            return JsonResponse({"code": -1, "message": "vm_nums is None"})
        for num in vm_nums:
            idcard = num.get("idcard")
            seq = num.get("seq")
            stu = Student.objects.get(num=idcard)
            if stu:
                stu.stu_vm_number = seq
                stu.save()
    return JsonResponse({"code": 1, "message": "ok"})

@license_required
@require_POST
@csrf_exempt
def verify_password(request):
    num = request.GET.get("num")
    password = request.GET.get("password")

    try:
        Student.objects.get(num=num, password=password)
    except Exception, e:
        LOG.error(e.message)
        return JsonResponse({"code": -1, "message": e.message})
    return JsonResponse({"code": 1, "message": "ok"})

@license_required
@require_GET
@csrf_exempt
def student_grade_vmnum(request):
    grade = request.GET.get("grade_id")
    vm_num = request.GET.get("vmnum")
    try:
        students = [{'id': x.id, 'name': x.name, "password": x.password, "num": x.num, "idcard": x.idcard, "gender": x.gender,
                 "vm_number": x.stu_vm_number, "grade_name": x.grade.name, "grade_id": x.grade.id} for x in [Student.objects.get(grade_id=grade, stu_vm_number=vm_num)]]
    except Exception, e:
        LOG.error(e.message)
        return JsonResponse({"code": -1, "message": e.message})
    return JsonResponse({"code": 1, "students": students})

@license_required
@require_GET
@csrf_exempt
def get_student_by_num(request):
    num = request.GET.get("num")
    try:
        students = [{'id': x.id, 'name': x.name, "password": x.password, "num": x.num, "idcard": x.idcard, "gender": x.gender,
                 "vm_number": x.stu_vm_number, "grade_name": x.grade.name, "grade_id": x.grade.id} for x in [Student.objects.get(num=num)]]
    except Exception, e:
        LOG.error(e.message)
        return JsonResponse({"code": -1, "message": e.message})
    return JsonResponse({"code": 1, "students": students})

@license_required
@require_POST
@csrf_exempt
def set_gradeclass_init(request):
    grade = request.POST.get("id")
    is_init = request.POST.get("is_init")
    try:
        g = Gradeclass.objects.get(id=grade)
        g.is_init = int(is_init)
        g.save()
    except Exception, e:
        LOG.error(e.message)
        return JsonResponse({"code": -1, "message": e.message})
    return JsonResponse({"code": 1, "message": "ok"})

@license_required
@require_GET
def make_symbolic_links(request):
    id = request.GET.get("id")
    students = Student.objects.filter(grade_id=id)
    for item in students:
        path_user = "/opt/user/" + item.num
        if not os.path.exists(path_user):
            os.makedirs(path_user)
        path_doc = "/opt/doc/stu_" + "%02d" % item.stu_vm_number
        if not os.path.exists(path_doc):
            os.makedirs(path_doc)
        os.symlink(path_user, path_doc + "/" + item.num)
    return JsonResponse({"code": 1, "message": "ok"})

@license_required
@require_GET
def delete_symbolic_links(request):
    id = request.GET.get("id")
    students = Student.objects.filter(grade_id=id)
    for item in students:
        path = "/opt/doc/stu_" + "%02d/" % item.stu_vm_number
        path += item.num
        if os.path.exists(path):
            os.remove(path)
    return JsonResponse({"code": 1, "message": "ok"})

def signature_passed(request):
    SecretId = "AKIDz8krbsJ5yKBZQpn74WFkmLPx3gnPhESA"
    secretKey = "Gu5t9xGARNpq86cd98joQYCN3Cozk1qA"
    if request.method == "GET":
        nonce = request.GET.get("Nonce")
        secretid = request.GET.get("SecretId")
        timestamp = request.GET.get("Timestamp")
        signature = request.GET.get("Signature")
    else:
        nonce = request.POST.get("Nonce")
        secretid = request.POST.get("SecretId")
        timestamp = request.POST.get("Timestamp")
        signature = request.POST.get("Signature")
    if not nonce or not nonce.isdigit():
        return {"code": 2001, "message": "Nonce:%s" % nonce}
    if not secretid:
        return {"code": 2002, "message": "SecretId:%s" % secretid}
    if not timestamp or not timestamp.isdigit():
        return {"code": 2003, "message": "Timestamp:%s" % timestamp}

    params = {"Nonce": nonce, "Timestamp": timestamp, "SecretId": secretid}
    url = request.method + request.path + "?" + "&".join(k + "=" + str(params[k]) for k in sorted(params.keys()))
    hashed = hmac.new(secretKey, url, hashlib.sha1)
    sign = binascii.b2a_base64(hashed.digest())[:-1]
    if sign == signature:
        return {"code": 200, "message": "ok"}
    else:
        return {"code": 2004, "message": "Signature is not passed!"}


