# -*- coding: utf-8 -*-

from common.models import Classroom

from utils import cacheutils


def is_in_class(course_id):
    classroom = cacheutils.get_classroom()
    if classroom and str(classroom.course_id) == str(course_id) and classroom.state != Classroom.ST_NORMAL:
        return True
    return False