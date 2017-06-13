# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db.models import Model, PositiveIntegerField, GenericIPAddressField, DateTimeField, ForeignKey
from utils.modelutils import GzippedDictField


class AuditLogEvent(object):

    USER_ADD = 1
    USER_EDIT = 2
    USER_REMOVE = 3

    COURSE_ADD = 10
    COURSE_EDIT = 11
    COURSE_REMOVE = 12
    COURSE_BEGIN = 13
    COURSE_FINISH = 14


class AuditLog(Model):

    actor = ForeignKey(User, null=True, blank=True)
    target_user = ForeignKey(User, null=True, blank=True)
    event = PositiveIntegerField(choices=(
        (AuditLogEvent.USER_ADD, 'user.add'),
        (AuditLogEvent.USER_EDIT, 'user.edit'),
        (AuditLogEvent.USER_REMOVE, 'user.remove'),
        (AuditLogEvent.COURSE_ADD, 'course.add'),
        (AuditLogEvent.COURSE_EDIT, 'course.edit'),
        (AuditLogEvent.COURSE_REMOVE, 'course.remove'),
        (AuditLogEvent.COURSE_BEGIN, 'course.begin'),
        (AuditLogEvent.COURSE_FINISH, 'course.finish'),
    ))
    ip_address = GenericIPAddressField(null=True, unpack_ipv4=True)
    data = GzippedDictField()
    datetime = DateTimeField(auto_now_add=True)

    def get_actor_name(self):
        if self.actor:
            return self.actor.username

    def get_note(self):
        if self.event == AuditLogEvent.USER_ADD:
            return 'added user {}'.format(self.target_user.username)
        elif self.event == AuditLogEvent.USER_EDIT:
            return 'edited user {}'.format(self.target_user.username)
        elif self.event == AuditLogEvent.USER_REMOVE:
            return 'removed user {}'.format(self.target_user.username)

        elif self.event == AuditLogEvent.COURSE_ADD:
            return 'added course {}'.format(self.data['course'])
        elif self.event == AuditLogEvent.COURSE_EDIT:
            return 'edited course {}'.format(self.data['course'])
        elif self.event == AuditLogEvent.COURSE_REMOVE:
            return 'remove course {}'.format(self.data['course'])
        elif self.event == AuditLogEvent.COURSE_BEGIN:
            return 'begin course {}'.format(self.data['course'])
        elif self.event == AuditLogEvent.COURSE_FINISH:
            return 'finished course {}'.format(self.data['course'])

        return ''
