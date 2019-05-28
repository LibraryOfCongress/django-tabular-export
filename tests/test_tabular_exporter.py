# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import unittest
import zipfile
from io import BytesIO

from django.db.models import Count
from django.http import HttpResponse, StreamingHttpResponse
from django.test.testcases import SimpleTestCase, TestCase
from django.test.utils import override_settings

from tabular_export.admin import ensure_filename
from tabular_export.core import (
    convert_value_to_unicode,
    export_to_csv_response,
    export_to_debug_html_response,
    export_to_excel_response,
    flatten_queryset,
    get_field_names_from_queryset,
    set_content_disposition,
)

from .models import TestModel


def assert_is_valid_xlsx(bytestream, required_filename="xl/worksheets/sheet1.xml"):
    # We'll confirm that it's returning a valid zip file but will trust the
    # Excel library's tests for the actual content:

    zf = zipfile.ZipFile(BytesIO(bytestream))
    zf.testzip()

    zip_filenames = zf.namelist()

    if required_filename not in zip_filenames:
        raise AssertionError(
            "Expected to find %s in %s" % (required_filename, zip_filenames)
        )


class SimpleUtilityTests(unittest.TestCase):
    longMessage = True

    def test_convert_value_to_unicode(self):
        self.assertEqual("", convert_value_to_unicode(None))
        self.assertEqual(
            b"\xc3\x9cnic\xc3\xb0e", convert_value_to_unicode("Ünicðe").encode("utf-8")
        )
        self.assertEqual(
            "2015-08-28T00:00:00",
            convert_value_to_unicode(datetime.datetime(year=2015, month=8, day=28)),
        )
        self.assertEqual(
            "2015-08-28",
            convert_value_to_unicode(datetime.date(year=2015, month=8, day=28)),
        )

    def test_set_content_disposition(self):
        # Since this is just supposed to add a key to a dict-like datastructure, we can fake it:
        def test_f(a1, a2, a3=None):
            self.assertEqual(a1, "not a real file")
            self.assertEqual(a2, "something")
            self.assertEqual(a3, "else")
            return {}

        decorated = set_content_disposition(test_f)

        self.assertEqual(
            {
                "Content-Disposition": "attachment; filename*=UTF-8''not%20a%20real%20file"
            },
            decorated("not a real file", "something", a3="else"),
        )

    def test_ensure_filename(self):
        # This decorator doesn't really need a ModelAdmin instance, just a valid Python object which
        # has a model property pointing to a Django model. Since we're just testing that custom and
        # model-derived filenames both work, we'll use mocks for both:

        class FakeModelAdmin(object):
            model = TestModel

        @ensure_filename("test")
        def fake_admin_action(
            modeladmin, request, queryset, filename=None, *args, **kwargs
        ):
            return filename

        fake_ma = FakeModelAdmin()

        # Confirm that the auto-generated filename
        self.assertEqual(
            "test models.test",
            fake_admin_action(fake_ma, None, None),
            msg="Standard filenames should be the model's verbose_name_plural with the "
            "provided extension",
        )
        self.assertEqual(
            "custom",
            fake_admin_action(fake_ma, None, None, filename="custom"),
            msg="Custom filenames should be passed through verbatim",
        )


class QuerySetTests(TestCase):
    longMessage = True

    def test_get_field_names_from_queryset(self):
        expected = ["id", "title"]

        qs = TestModel.objects.all()
        # QuerySet, ValuesQuerySet and ValuesListQuerySet should always work:
        self.assertListEqual(expected, get_field_names_from_queryset(qs.all()))
        self.assertListEqual(expected, get_field_names_from_queryset(qs.values()))
        self.assertListEqual(expected, get_field_names_from_queryset(qs.values_list()))

    def test_get_field_names_from_queryset_extra(self):
        expected = ["id", "title", "upper_title"]

        qs = TestModel.objects.extra(select={"upper_title": "UPPER(TITLE)"})
        # QuerySet, ValuesQuerySet and ValuesListQuerySet should always work:
        self.assertListEqual(expected, get_field_names_from_queryset(qs.all()))
        self.assertListEqual(expected, get_field_names_from_queryset(qs.values()))
        self.assertListEqual(expected, get_field_names_from_queryset(qs.values_list()))

    def test_get_field_names_from_queryset_annotate(self):
        expected = ["id", "title", "tags__count"]

        qs = TestModel.objects.annotate(Count("tags"))
        # QuerySet, ValuesQuerySet and ValuesListQuerySet should always work:
        self.assertListEqual(expected, get_field_names_from_queryset(qs.all()))
        self.assertListEqual(expected, get_field_names_from_queryset(qs.values()))
        self.assertListEqual(expected, get_field_names_from_queryset(qs.values_list()))

    def test_flatten_queryset(self):
        TestModel.objects.create(pk=1, title="ABC")

        headers, rows = flatten_queryset(TestModel.objects.all())
        self.assertListEqual(["ID", "title"], headers)
        self.assertListEqual(list(rows), [(1, "ABC")])

        headers, rows = flatten_queryset(TestModel.objects.all(), field_names=["title"])
        self.assertListEqual(["title"], headers)
        self.assertListEqual(list(rows), [("ABC",)])

        headers, rows = flatten_queryset(
            TestModel.objects.all(),
            field_names=["title"],
            extra_verbose_names={"title": "The Title"},
        )
        self.assertListEqual(
            ["The Title"],
            headers,
            msg="extra_verbose_names must override default headers",
        )
        self.assertListEqual(list(rows), [("ABC",)])


class ResponseTests(SimpleTestCase):
    longMessage = True

    def get_test_data(self):
        # This exercises the core types: numbers, strings and dates
        return (
            ["Foo Column", "Bar Column"],
            (
                (1, 2),
                (3, 4),
                ("abc", "def"),
                (
                    datetime.datetime(year=2015, month=8, day=28),
                    datetime.date(year=2015, month=8, day=28),
                ),
            ),
        )

    def test_export_to_debug_html_response(self):
        headers, rows = self.get_test_data()
        resp = export_to_debug_html_response("test.html", headers, rows)
        self.assertNotIn("Content-Disposition", resp)

    def test_export_to_excel_response(self):
        headers, rows = self.get_test_data()
        resp = export_to_excel_response("test.xlsx", headers, rows)
        self.assertEqual(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resp["Content-Type"],
        )
        self.assertEqual(
            "attachment; filename*=UTF-8''test.xlsx", resp["Content-Disposition"]
        )

        assert_is_valid_xlsx(resp.content)

    def test_export_to_csv_response(self):
        headers, rows = self.get_test_data()
        resp = export_to_csv_response("test.csv", headers, rows)
        content = [i.decode("utf-8") for i in resp.streaming_content]
        self.assertEqual("text/csv; charset=utf-8", resp["Content-Type"])
        self.assertEqual(
            "attachment; filename*=UTF-8''test.csv", resp["Content-Disposition"]
        )
        self.assertEqual(
            content,
            [
                "Foo Column,Bar Column\r\n",
                "1,2\r\n",
                "3,4\r\n",
                "abc,def\r\n",
                "2015-08-28T00:00:00,2015-08-28\r\n",
            ],
        )

    @override_settings(TABULAR_RESPONSE_DEBUG=True)
    def test_return_debug_reponse(self):
        headers, rows = self.get_test_data()

        resp = export_to_excel_response("test.xlsx", headers, rows)
        self.assertEqual("text/html; charset=UTF-8", resp["Content-Type"])
        self.assertNotIn("Content-Disposition", resp)

        self.assertInHTML(
            "<th>Foo Column</th>",
            "".join(i.decode("utf-8") for i in resp.streaming_content),
        )

    def test_export_csv_using_generator(self):
        headers = ["A Number", "Status"]

        def my_generator():
            for i in range(0, 1000):
                yield (i, "\N{WARNING SIGN}")

        resp = export_to_csv_response("numbers.csv", headers, my_generator())
        self.assertIsInstance(resp, StreamingHttpResponse)
        self.assertEqual(
            "attachment; filename*=UTF-8''numbers.csv", resp["Content-Disposition"]
        )

        # exhaust the iterator:
        content = list(i.decode("utf-8") for i in resp.streaming_content)
        # We should have one header row + 1000 content rows:
        self.assertEqual(len(content), 1001)
        self.assertEqual(content[0], "A Number,Status\r\n")
        self.assertEqual(content[-1], "999,\u26a0\r\n")

    def test_export_excel_using_generator(self):
        headers = ["A Number", "Status"]

        def my_generator():
            for i in range(0, 1000):
                yield (i, "\N{WARNING SIGN}")

        resp = export_to_excel_response("numbers.xlsx", headers, my_generator())
        # xlsxwriter doesn't allow streaming generation of XLSX files:
        self.assertIsInstance(resp, HttpResponse)
        self.assertEqual(
            "attachment; filename*=UTF-8''numbers.xlsx", resp["Content-Disposition"]
        )
