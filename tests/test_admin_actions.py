# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals
import unittest

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import User
try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse
from django.test.testcases import TestCase

from .models import TestModel
from .test_tabular_exporter import assert_is_valid_xlsx


class TestAdminActions(TestCase):
    """Tests which use the full admin application"""
    longMessage = True

    @classmethod
    def setUpClass(cls):
        User.objects.create_superuser('test_admin', 'root@example.org', 'TEST')

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(username='test_admin').delete()

    def setUp(self):
        super(TestAdminActions, self).setUp()

        assert self.client.login(username='test_admin', password='TEST')

        TestModel.objects.create(pk=1, title='TEST ITEM 1')
        TestModel.objects.create(pk=2, title='TEST ITEM 2')

    def test_export_to_excel_action(self):
        changelist_url = reverse('admin:tests_testmodel_changelist')

        data = {'action': 'export_to_excel_action',
                'select_across': 1,
                'index': 0,
                ACTION_CHECKBOX_NAME: TestModel.objects.first().pk}
        response = self.client.post(changelist_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Content-Disposition', response)
        self.assertEqual("attachment; filename*=UTF-8''test%20models.xlsx",
                         response['Content-Disposition'])
        self.assertEqual('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         response['Content-Type'])

        assert_is_valid_xlsx(response.content)

    def test_export_to_csv_action(self):
        changelist_url = reverse('admin:tests_testmodel_changelist')

        data = {'action': 'export_to_csv_action',
                'select_across': 1,
                'index': 0,
                ACTION_CHECKBOX_NAME: TestModel.objects.first().pk}
        response = self.client.post(changelist_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Content-Disposition', response)
        self.assertEqual("attachment; filename*=UTF-8''test%20models.csv",
                         response['Content-Disposition'])
        self.assertEqual('text/csv; charset=utf-8',
                         response['Content-Type'])

        content = list(i.decode('utf-8') for i in response.streaming_content)
        self.assertEqual(len(content), TestModel.objects.count() + 1)
        self.assertRegexpMatches(content[0], r'^ID,title,tags_count')
        self.assertRegexpMatches(content[1], r'^1,TEST ITEM 1,0\r\n')
        self.assertRegexpMatches(content[2], r'^2,TEST ITEM 2,0\r\n')

    @unittest.skip("error (where is custom export configured?)")
    def test_custom_export_to_csv_action(self):
        changelist_url = reverse('admin:tests_testmodel_changelist')

        data = {'action': 'custom_export_to_csv_action',
                'select_across': 1,
                'index': 0,
                ACTION_CHECKBOX_NAME: TestModel.objects.first().pk}
        response = self.client.post(changelist_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Content-Disposition', response)
        self.assertEqual("attachment; filename*=UTF-8''test%20models.csv",
                         response['Content-Disposition'])
        self.assertEqual('text/csv; charset=utf-8',
                         response['Content-Type'])

        content = list(i.decode('utf-8') for i in response.streaming_content)
        self.assertEqual(len(content), TestModel.objects.count() + 1)
        self.assertRegexpMatches(content[0], r'^ID,title,number of tags')
        self.assertRegexpMatches(content[1], r'^1,TEST ITEM 1,0\r\n')
        self.assertRegexpMatches(content[2], r'^2,TEST ITEM 2,0\r\n')
