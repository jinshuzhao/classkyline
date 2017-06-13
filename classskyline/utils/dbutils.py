# -*- coding: utf-8 -*-
from django.dispatch import Signal
from django.db import close_old_connections


thread_started = Signal()
thread_started.connect(close_old_connections)
thread_finished = Signal()
thread_finished.connect(close_old_connections)
