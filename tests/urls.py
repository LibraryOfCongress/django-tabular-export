# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from django.urls import path
from django.contrib import admin

urlpatterns = [
    path("admin/", admin.site.urls),
]
