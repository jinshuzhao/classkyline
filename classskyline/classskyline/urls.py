from django.conf.urls import patterns, include, url
from django.contrib import admin


urlpatterns = patterns(
    '',
    url(r'^$', 'cloudclass.views.dash_board'),
    url(r'^login/$', 'django.contrib.auth.views.login', name='login', ),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'template_name': 'registration/login.html'}, name='logout'),
    url(r'^password_change/$', 'django.contrib.auth.views.password_change', name='password_change'),
    url(r'^password_change/done/$', 'django.contrib.auth.views.password_change_done', name='password_change_done'),

    # url(r'^admin/', include(admin.site.urls)),

    url(r'^cloudclass/', include("cloudclass.urls")),
    url(r'^api/', include('api.urls'))
)
