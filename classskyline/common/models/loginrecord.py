# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Model


class LoginRecord(Model):
    studentnum = models.CharField(max_length=20, blank=True)
    date_login = models.DateTimeField(auto_now_add=True)