# -*- coding: utf-8 -*-
from functools import wraps

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import available_attrs

from utils import cacheutils
from utils import fileutils


class HttpResponseNoContent(HttpResponse):
    status_code = 204


class HttpResponseNotAuthorized(HttpResponse):
    status_code = 401


class HttpResponseConflict(HttpResponse):
    status_code = 409


class JsonResponseBadRequest(JsonResponse):
    status_code = 400


class JsonResponseForbidden(JsonResponse):
    status_code = 403


class JsonResponseNotFound(JsonResponse):
    status_code = 404


class JsonResponseConflict(JsonResponse):
    status_code = 409


class JsonResponseServerError(JsonResponse):
    status_code = 500


ERROR_CODES = {
    0: u'正常。',
    4000: u'错误请求。',
    4030: u'非法请求。',
    4031: u'授权无效。',
    4032: u'认证失败。',
    4040: u'找不到资源。',
    4041: u'找不到教室。',
    4042: u'找不得基础镜像。',
    4043: u'找不到课程镜像。',
    4044: u'找不到课程。',
    4045: u'找不到云桌面。',
    4046: u'找不到网络设置。',
    4090: u'发生冲突。',
    4091: u'资源尚未就绪。',
    4092: u'处于上课状态。'
}


def fmt_error(code, extra_msg=u''):
    return {
        'code': code,
        'message': u'{}{}'.format(ERROR_CODES[code], extra_msg),
    }


def license_required(view_func):
    """
    Decorator to make a view only accept requests when license is not expired.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        lic = cacheutils.get_license()
        if lic is None:
            if cacheutils.get_trail() < 0:
                return JsonResponseForbidden(fmt_error(4031, u'试用已过期，请联系管理员。'))
        elif not fileutils.validate_license(lic, cacheutils.get_nics()):
                return JsonResponseForbidden(fmt_error(4031, u'授权已过期，请联系管理员。'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def authenticate_required(view_func):
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated():
            return JsonResponseForbidden(fmt_error(4032, u'用户未登录。'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view
