from django.test import TestCase
from django.test.client import Client
import unittest
from common.Models_create import *
from django.contrib.auth.models import User
from views import *
import datetime
from django.utils import timezone
from django.test import RequestFactory
from django.contrib.auth import authenticate, login
from django.core.urlresolvers import reverse

# RequestFactory : mock the request .
# request_factory = RequestFactory()
# Create your tests here
class CloudClassUrlRefTest(unittest.TestCase):
    def setUp(self, name="Neil", mail="Neil@qq.com", pwd="NeilPassword" ):
        self.client = Client()
        #self.user = User.objects.get(name, mail, pwd)
        try:
            user_tmp = User.objects.get(username=name)
            #print user_tmp
        except:
            User.objects.create_user(name, mail, pwd)

    def test_dash_board(self):
        self.client.login(username = "Neil", password = "NeilPassword")
        res = self.client.get("/cloudclass/")
        self.client.logout()
        self.assertEqual(res.status_code, 200)

    def test_course_list(self):
        self.client.login(username="Neil", password="NeilPassword")
        res = self.client.get("/cloudclass/course/")
        #print "res_01 = ", res.status_code
        self.client.logout()
        self.assertEqual(res.status_code, 200)

    def test_desktop_list(self):
        self.client.login(username="Neil", password="NeilPassword")
        res = self.client.get("/cloudclass/desktop/")
        self.client.logout()
        self.assertEqual(res.status_code, 200)

    def ttest_tools_list(self):
        self.client.login(username="Neil", password="NeilPassword")
        res = self.client.get("/cloudclass/tools/")
        print "res_002", res.status_code
        self.assertEqual(res.status_code, 200)

    def test_add_course(self):
        self.client.login(username = "Neil", password="NeilPassword")
        res = self.client.get("/cloudclass/addcourse/")
        #print("res_003", res.status_code)
        self.assertEqual(res.status_code,200)

    def test_editstrategory(self):
        self.client.login(username="Neil", password="NeilPassword")
        res = self.client.get("/cloudclass/editstrategory/")
        #print("res_004",res.status_code)
        self.client.logout()
        self.assertEqual(res.status_code, 200)

    def test_ajaxgetcourses(self):
        host = create_host()
        profile = create_course_profile()
        create_course(uuid="3000", visibility=0, host=host, profile=profile)
        create_course(uuid="3001", visibility=1, host=host, profile=profile)
        create_course(uuid="3002", visibility=2, host=host, profile=profile)
        self.client.login(username="Neil", password="NeilPassword")
        res = self.client.get("/cloudclass/ajaxgetcourses/")

        print "res_005", res.status_code



