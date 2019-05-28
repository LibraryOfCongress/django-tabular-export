# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [url(r"^admin/", include(admin.site.urls))]
