from django.test import TestCase
import unittest
from views import *
from utils.vendor.IPy import IP
from utils.vendor import ipaddress
import datetime
from django.utils import timezone
from common.models import *
from django.test import RequestFactory
from common.Models_create import *
import os, sys

# RequestFactory : mock the request .
#request_factory = RequestFactory()
#request = request_factory.post('/fake-path', data={'name': u'Waldo'})
# Create your tests here.


class ApiBaseTest(unittest.TestCase):
    def test_begin_course_get(self):
        request_factory = RequestFactory()
        request = request_factory.get("./")
        response  = begin_course(request)
        self.assertEqual(response.status_code,405)

    def test_begin_course_post(self):
        request_factory = RequestFactory()
        request = request_factory.post("./", {"uuid":"1001"})
        response  = begin_course(request)
        self.assertEqual(response.status_code, 404 )

    def test_get_courses_post(self):
        request_factory = RequestFactory()
        request = request_factory.post("./")
        response  = get_courses(request)
        #print response.status_code
        self.assertEqual(response.status_code,405)

    def test_get_courses_get(self):
        request_factory = RequestFactory()
        request = request_factory.get("./")
        response  = get_courses(request)
        #print response.status_code
        self.assertEqual(response.status_code,200)

    def test_free_course_post(self):
        request_factory = RequestFactory()
        request = request_factory.post("./",{"uuid":"1004"})
        response  = free_course(request)
        #print response.status_code
        self.assertEqual(response.status_code,404)

    def test_free_course_get(self):
        request_factory = RequestFactory()
        request = request_factory.get("./")
        response  = free_course(request)
        #print response.status_code
        self.assertEqual(response.status_code,405)

    def test_finish_course_post(self):
        request_factory = RequestFactory()
        request = request_factory.post("./",{"uuid":"1005"})
        response  = finish_course(request)
        #print response.status_code
        self.assertEqual(response.status_code,404)

    def test_free_course_get(self):
        request_factory = RequestFactory()
        request = request_factory.get("./")
        response  = finish_course(request)
        #print response.status_code
        self.assertEqual(response.status_code,405)

    def test_free_course_post(self):
        request_factory = RequestFactory()
        request = request_factory.post("./",{"uuid":"1005"})
        response  = free_course(request)
        print response.status_code
        self.assertEqual(response.status_code,404)


class ApiBeginCourseTestTestCase(TestCase):
    def test_begin_course(self):
        create_network()
        host = create_host()
        profile = create_course_profile()
        create_course(uuid="2001", host=host, profile=profile)
        response = self.client.post("/api/begin_course",{"uuid":"2001"})
        print sys._getframe().f_code.co_name, response.status_code






