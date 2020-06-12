# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import models


class TestModel(models.Model):
    title = models.CharField(max_length=100)

    tags = models.ManyToManyField("TestModelTag")

    class Meta(object):
        ordering = ("pk",)


class TestModelTag(models.Model):
    title = models.CharField(max_length=100)
