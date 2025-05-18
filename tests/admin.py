# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib import admin
from django.db.models import Count

from tabular_export.admin import export_to_csv_action, export_to_excel_action

from .models import TestModel


class TestModelAdmin(admin.ModelAdmin):
    actions = (export_to_excel_action, export_to_csv_action)

    # For testing, we'll make this more complicated by adding a computed column:
    list_display = ("title", "tags_count")

    def tags_count(self, obj):
        return obj.tags_count

    tags_count.short_description = "Tags Count"
    tags_count.admin_order_field = "tags_count"

    def get_queryset(self, *args, **kwargs):
        return self.model.objects.all().annotate(
            tags_count=Count("tags", distinct=True)
        )

    def custom_export_to_csv_action(self, request, queryset):
        # Add a custom action with the extra verbose name "number of tags"
        return export_to_csv_action(
            self,
            request,
            queryset,
            extra_verbose_names={"tags_count": "number of tags"},
        )

    actions = (
        export_to_excel_action,
        export_to_csv_action,
        custom_export_to_csv_action,
    )


admin.site.register(TestModel, TestModelAdmin)
