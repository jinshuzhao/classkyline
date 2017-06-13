# -*- coding: utf-8 -*-
from decimal import Decimal
from calendar import monthrange
import datetime
import json

import pytz
from django.utils import timezone


class JsonHelper(object):

    @staticmethod
    def format(code=1, message=""):
        result = {}
        result["code"] = code
        result["message"] = str(message)
        return result
        # return json.dumps(result)

    @staticmethod
    def get_dict_value(dict, key):
        if key in dict:
            result = dict[key]
            if result is None:
                result = ""
            return result
        return ""


class DatetimeHelper(object):

    @staticmethod
    def safe_new_datetime(d):
        kw = [d.year, d.month, d.day]
        if isinstance(d, datetime.datetime):
            kw.extend([d.hour, d.minute, d.second, d.microsecond, d.tzinfo])
        return datetime.datetime(*kw)

    @staticmethod
    def safe_new_date(d):
        return datetime.date(d.year, d.month, d.day)

    @staticmethod
    def convert_string_to_UTC(str_dt, format):
        """
        日期字符串转化为 UTC时间
        """
        local = timezone.get_default_timezone()
        native = datetime.datetime.strptime(str_dt, format)
        local_dt = local.localize(native, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        return utc_dt

    @staticmethod
    def convert_to_native(utc_date):
        """
        日期字符串转化为 UTC时间
        """
        local = timezone.get_default_timezone()
        result = utc_date.astimezone(local)
        return result

    @staticmethod
    def convert_string_to_native(str_dt, format):
        """
        日期字符串转化为 UTC时间
        """
        tz = timezone.get_default_timezone()
        native = datetime.datetime.strptime(str_dt, format)
        return tz.localize(native)

    @staticmethod
    def UTC_date_now():
        """
        获取当前的UTC日期：不包括时间的情况下转化UTC时间
        """
        dt_date = datetime.datetime.now().date()
        return DatetimeHelper.convert_string_to_UTC(str(dt_date), "%Y-%m-%d")

    @staticmethod
    def add_months(dt, months):
        month = dt.month - 1 + months
        year = dt.year + month / 12
        month = month % 12 + 1
        day = min(dt.day, monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)


class DatetimeJSONEncoder(json.JSONEncoder):
    """可以序列化时间的JSON"""

    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"

    def default(self, o):
        if isinstance(o, datetime.datetime):
            d = DatetimeHelper.safe_new_datetime(o)
            return d.strftime("%s %s" % (self.DATE_FORMAT, self.TIME_FORMAT))
        elif isinstance(o, datetime.date):
            d = DatetimeHelper.safe_new_date(o)
            return d.strftime(self.DATE_FORMAT)
        elif isinstance(o, datetime.time):
            return o.strftime(self.TIME_FORMAT)
        elif isinstance(o, Decimal):
            return str(o)
        else:
            return super(DatetimeJSONEncoder, self).default(o)


def form_error_msg(errors):
    """
    :param errors: the errors that form return
    :return:  msg, string, the error message
    构造from错误信息输出 
    """
    msgs = [e[0] for e in errors.values()]
    msg = ' '.join(msgs)
    return msg