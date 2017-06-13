# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Model, ForeignKey
from common.models.gradeclass import Gradeclass


class Student(Model):
    _male = 1
    _female = 0
    name = models.CharField(max_length=50, blank=True)
    password = models.CharField(max_length=100, blank=True)
    num = models.CharField(max_length=20, blank=True)
    idcard = models.CharField(max_length=20, blank=True)
    gender = models.PositiveIntegerField({(_male, u"男"), (_female, u"女")})
    grade = ForeignKey(Gradeclass)
    stu_vm_number = models.IntegerField(blank=True, null=True)


    def save(self, student=None, grade_id=None):
        print student
        print grade_id
        if student and grade_id:
            self.name = student[0]
            self.num = student[1]
            self.password = student[2]
            self.idcard = student[3]
            self.gender = student[4]
            grade = Gradeclass.objects.get(id=grade_id)
            self.grade = grade
            self.stu_vm_number = student[6]
        super(Student, self).save()




