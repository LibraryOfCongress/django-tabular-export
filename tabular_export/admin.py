# encoding: utf-8
"""
Usage can be as simple as adding the generic actions to a ModelAdmin::

    actions = (export_to_excel_action, export_to_csv_action)

These will take the QuerySet and provide a generic export action which is essentially what you'd from the
``values()`` method. The filename will be generated from the model name specified for that `ModelAdmin`.

The allow you to pass a custom file filename or list of fields which are passed through directly to
:func:`flatten_queryset` and :func:`export_to_excel_response` / :func:`export_to_csv_response`
"""
from __future__ import absolute_import, division, print_function

from functools import wraps

from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from .core import export_to_csv_response, export_to_excel_response, flatten_queryset


def ensure_filename(suffix):
    """
    Decorator which automatically sets the filename going into the admin actions
    from the ``ModelAdmin.model``'s ``verbose_name_plural`` value unless a value
    was provided by the caller.
    """

    def outer(f):
        # TODO: After upgrading to Python 3, we can drop the extra args using , *, to force keyword-only args
        @wraps(f)
        def inner(modeladmin, request, queryset, filename=None, *args, **kwargs):
            if filename is None:
                filename = '%s.%s' % (force_text(modeladmin.model._meta.verbose_name_plural), suffix)
            return f(modeladmin, request, queryset, filename=filename, *args, **kwargs)
        return inner
    return outer


@ensure_filename('xlsx')
def export_to_excel_action(modeladmin, request, queryset, filename=None, field_names=None, extra_verbose_names=None):
    """Django admin action which exports selected records as an Excel XLSX download"""
    headers, rows = flatten_queryset(queryset, field_names=field_names, extra_verbose_names=extra_verbose_names)
    return export_to_excel_response(filename, headers, rows)


export_to_excel_action.short_description = _('Export to Excel')


@ensure_filename('csv')
def export_to_csv_action(modeladmin, request, queryset, filename=None, field_names=None, extra_verbose_names=None):
    """Django admin action which exports the selected records as a CSV download"""
    headers, rows = flatten_queryset(queryset, field_names=field_names, extra_verbose_names=extra_verbose_names)
    return export_to_csv_response(filename, headers, rows)


export_to_csv_action.short_description = _('Export to CSV')
