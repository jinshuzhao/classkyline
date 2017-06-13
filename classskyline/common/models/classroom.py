# -*- coding: utf-8 -*-
from django.db import models
from common.models.course import Course
from common.models.host import Host


class Classroom(models.Model):

    ST_NORMAL = 0
    ST_PRE_CLASS = 1
    ST_ON_CLASS = 2
    ST_POST_CLASS = 3

    name = models.CharField(max_length=256)
    seats = models.SmallIntegerField()  # 瘦客户机数量
    state = models.PositiveSmallIntegerField(choices=(
        (ST_NORMAL, u'初始状态'),
        (ST_PRE_CLASS, u'准备上课'),
        (ST_ON_CLASS, u'正在上课'),
        (ST_POST_CLASS, u'准备下课'),
    ), default=ST_NORMAL)  # 上课状态
    host = models.ForeignKey(Host)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL)  # 当前上课的课程

    def __unicode__(self):
        return u'<{}: {} [SEATS: {}, STATE: {}, HOST: {}, COURSE: {}]>'.format(
            self.__class__.__name__,
            self.name,
            self.seats,
            self.get_state_display(),
            self.host.ip_address,
            self.course.name if self.course else None)
