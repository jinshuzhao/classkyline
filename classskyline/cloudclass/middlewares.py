# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.shortcuts import redirect

from utils.settingsutils import OptsMgr, INITIALIZED


class InitCheckMiddleware(object):

    def process_request(self, request):
        init_step_1 = reverse('init_guide', kwargs={'step': 1})
        init_step_2 = reverse('init_guide', kwargs={'step': 2})
        init_step_3 = reverse('init_guide', kwargs={'step': 3})
        stack_backends = reverse('stack_backends')
        set_host = reverse('set_host')
        param_set = reverse('param_set')

        init_related_url = (init_step_1, init_step_2, init_step_3, stack_backends, set_host, param_set)

        if OptsMgr.get_value(INITIALIZED):
            if request.path in init_related_url:
                return redirect(reverse('dash_board'))
        else:
            if request.path not in init_related_url:
                return redirect(init_step_1)
