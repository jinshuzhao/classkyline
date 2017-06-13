# -*- coding: utf-8 -*-
from __future__ import unicode_literals  # IMPORTANT!!

from django import forms
from django.contrib.auth.models import User

from common.models.image import OS_TYPE_CHOICES, OS_VERSION_CHOICES
from common.models import BaseImage, CourseProfile, Course, Gradeclass, Student
from utils import cacheutils
import logging
LOG = logging.getLogger(__name__)


class OSInfoForm(forms.Form):
    CAPACITY_CHOICES = (
        ('', '------'),
        (10240, '10G'),
        (20480, '20G'),
        (30720, '30G'),
        (40960, '40G'),
        (51200, '50G')
    )

    os_type = forms.IntegerField(label='操作系统类型', widget=forms.Select(choices=OS_TYPE_CHOICES))
    os_version = forms.IntegerField(label='操作系统版本', widget=forms.Select(choices=OS_VERSION_CHOICES))
    capacity = forms.IntegerField(label='硬盘大小', widget=forms.Select(choices=CAPACITY_CHOICES))

    def __init__(self, *args, **kwargs):
        super(OSInfoForm, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class BaseImageForm(OSInfoForm):
    name = forms.CharField(label='镜像名称')

    def __init__(self, *args, **kwargs):
        super(BaseImageForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        """ 保持name唯一 """
        name = self.cleaned_data.get('name')
        try:
            BaseImage.objects.get(name=name)
            raise forms.ValidationError('镜像名称不能重复')
        except BaseImage.DoesNotExist:
            return name
        except BaseImage.MultipleObjectsReturned:
            raise forms.ValidationError('返回多个值')

    def save(self, image_path, refname, commit=True):
        base_image = BaseImage(name=self.cleaned_data.get('name'),
                               refname=refname,
                               capacity=self.cleaned_data.get('capacity'),
                               image_path=image_path,
                               os_type=self.cleaned_data.get('os_type'),
                               os_version=self.cleaned_data.get('os_version'))
        if commit:
            base_image.save()
        return base_image


class AddBaseInfoForm(OSInfoForm):
    name = forms.CharField(label='名称')

    def __init__(self, image_id=None, *args, **kwargs):
        self.image_id = image_id
        super(AddBaseInfoForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        try:
            base_image = BaseImage.objects.get(name=self.cleaned_data['name'])
            if str(base_image.id) == str(self.image_id):
                return self.cleaned_data['name']
            raise forms.ValidationError('镜像名称已经存在,不能重名')
        except BaseImage.DoesNotExist:
            return self.cleaned_data['name']

    def save(self, commit=True):
        base_image = BaseImage.objects.get(id=self.image_id)

        os_type = self.cleaned_data.get('os_type')
        os_version = self.cleaned_data.get('os_version')
        capacity = self.cleaned_data.get('capacity')
        name = self.cleaned_data.get('name')

        if commit:
            base_image.os_type = os_type
            base_image.os_version = os_version
            base_image.capacity = capacity
            base_image.name = name
            base_image.save()
            return base_image


class EditBaseImageNameForm(forms.Form):
    name = forms.CharField(label='名称')

    def __init__(self, image_id=None, *args, **kwargs):
        self.image_id = image_id
        super(EditBaseImageNameForm, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_name(self):
        try:
            base_image = BaseImage.objects.get(name=self.cleaned_data['name'])
            if str(base_image.id) == str(self.image_id):
                return self.cleaned_data['name']
            raise forms.ValidationError('镜像名称已经存在,不能重名')
        except BaseImage.DoesNotExist:
            return self.cleaned_data['name']

    def save(self, commit=True):
        base_image = BaseImage.objects.get(id=self.image_id)

        if commit:
            base_image.name = self.cleaned_data['name']
            base_image.save()
        return base_image


class CourseImageForm(forms.Form):

    name = forms.CharField(label='课程名称')
    desc = forms.CharField(label='课程描述', widget=forms.Textarea(attrs={'cols': '40', 'rows': '3'}), required=False)
    base_image = forms.IntegerField(label='镜像列表', widget=forms.Select(), initial='请选择镜像', required=False)
    os_version = forms.CharField(label='操作系统版本', required=False)
    visibility = forms.IntegerField(label='是否启用', widget=forms.RadioSelect(choices=((1, '启用',), (0, '禁用'))))
    course_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    profile = forms.IntegerField(label='系统配置', widget=forms.RadioSelect())

    def clean_name(self):
        try:
            course = Course.objects.get(name=self.cleaned_data.get('name'))
            if str(course.id) == str(self.course_id):
                return self.cleaned_data.get('name')
            raise forms.ValidationError(u'该名称已经存在')
        except Course.DoesNotExist:
            return self.cleaned_data.get('name')

    def __init__(self, course_id=None, *args, **kwargs):
        self.course_id = course_id
        super(CourseImageForm, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

        base_images = BaseImage.objects.filter(os_version__isnull=False, published=True)
        image_choices = [(img.id, img.name) for img in base_images]
        image_choices.insert(0, ('', '请选择镜像'))

        # course profile 选项
        course_profiles = CourseProfile.objects.all()
        course_profile_choices = [(cp.id, cp.name) for cp in course_profiles]

        self.fields['base_image'].widget.choices = image_choices
        self.fields['os_version'].widget.attrs.update({'disabled': 'disabled'})
        self.fields['profile'].widget.choices = course_profile_choices

    def save(self, image=None, refname=None):
        data = self.cleaned_data
        data.pop('base_image')
        data.pop('os_version')
        data.pop('course_id')

        if refname:
            data['refname'] = refname

        if self.course_id:
            # 编辑
            courses = Course.objects.filter(id=self.course_id)
            courses.update(**data)
            for course in courses:
                cacheutils.clear_course(course)
        else:
            # 新建
            profile = CourseProfile.objects.get(id=data['profile'])
            data['profile'] = profile
            data.update({'image': image})
            return Course.objects.create(**data)


class TeacherForm(forms.Form):
    username = forms.CharField(label='用户名', widget=forms.TextInput())
    first_name = forms.CharField(label='姓名', widget=forms.TextInput(), required=False)
    password = forms.CharField(label='密码', widget=forms.PasswordInput())
    password1 = forms.CharField(label='确认密码', widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super(TeacherForm, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_username(self):
        try:
            User.objects.get(username=self.cleaned_data.get('username'))
            raise forms.ValidationError('该用户名已存在')
        except User.DoesNotExist:
            return self.cleaned_data.get('username')

    def clean_password1(self):
        password = self.cleaned_data.get('password')
        password1 = self.cleaned_data.get('password1')
        if password and password1 and password == password1:
            return password
        raise forms.ValidationError('密码不一致')

    def save(self, commit=True):
        data = self.cleaned_data
        username = data.get('username')
        first_name = data.get('first_name')
        password = data.get('password')

        if commit:
            User.objects._create_user(
                username=username,
                first_name=first_name,
                password=password,
                email=None,
                is_staff=True,
                is_superuser=False
            )


class TeacherEditForm(forms.Form):
    teacher_id = forms.IntegerField(label='id', widget=forms.HiddenInput())
    new_password = forms.CharField(label='新密码', widget=forms.PasswordInput())
    re_password = forms.CharField(label='确认密码', widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super(TeacherEditForm, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_re_password(self):
        new_password = self.cleaned_data.get('new_password')
        re_password = self.cleaned_data.get('re_password')

        if new_password and re_password and new_password == re_password:
            return re_password
        raise forms.ValidationError('密码不一致')

    def save(self, commit=True):
        if commit:
            teacher = User.objects.get(id=self.cleaned_data.get('teacher_id'))
            teacher.set_password(self.cleaned_data.get('re_password'))
            teacher.save()
            return teacher


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(label='当前密码', widget=forms.PasswordInput())
    new_password = forms.CharField(label='新密码', widget=forms.PasswordInput())
    re_password = forms.CharField(label='确认密码', widget=forms.PasswordInput())

    def __init__(self, request, *args, **kwargs):
        super(PasswordChangeForm, self).__init__(*args, **kwargs)
        self.user = request.user
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        is_valid = self.user.check_password(current_password)
        if is_valid:
            return current_password
        raise forms.ValidationError('当前密码不正确')

    def clean_re_password(self):
        new_password = self.cleaned_data.get('new_password')
        re_password = self.cleaned_data.get('re_password')

        if new_password == re_password:
            return re_password
        raise forms.ValidationError('两次密码输入不一致')

    def save(self):
        self.user.set_password(self.cleaned_data.get('re_password'))
        self.user.save()
        return self.user


class GradeForm(forms.Form):
    gradename = forms.CharField(label='班级名称', widget=forms.TextInput(attrs={"autocomplete": "off"}))
    gradeinfo = forms.CharField(label='说明', widget=forms.Textarea(attrs={"rows": 3, "autocomplete": "off"}), required=False)

    def __init__(self, *args, **kwargs):
        super(GradeForm, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self):
        data = self.cleaned_data
        gradename = data.get('gradename')
        info = data.get('gradeinfo')

        try:
            Gradeclass.objects.get(name=gradename)
            return {"code": -1, "message": u"已班级名称存在班级"}
        except Exception, e:
            grade = Gradeclass()
            grade.name = gradename
            grade.description = info
            grade.seq = 0
            grade.is_init = 0
            grade.save()
        return {"code": 1, "message": u"ok"}


class GradeEditForm(forms.Form):
    grade_id = forms.CharField(label='id', widget=forms.HiddenInput)
    gradename_edit = forms.CharField(label='班级名称', widget=forms.TextInput(attrs={"autocomplete": "off"}))
    gradeinfo_edit = forms.CharField(label='说明', widget=forms.Textarea(attrs={"rows": 3, "autocomplete": "off"}), required=False)

    def __init__(self, *args, **kwargs):
        super(GradeEditForm, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self):
        data = self.cleaned_data
        grade_id = data.get('grade_id')
        gradename_edit = data.get('gradename_edit')
        gradeinfo_edit = data.get('gradeinfo_edit')
        grade = Gradeclass.objects.filter(name=gradename_edit).exclude(id=grade_id)
        if grade:
            return {"code": -1, "message": "改班级名字已存在!"}
        g = Gradeclass.objects.get(id=grade_id)
        g.name = gradename_edit
        g.description = gradeinfo_edit
        g.seq = 0
        g.is_init = 0
        g.save()
        return {"code": 1, "message": "ok"}


class StudentForm(forms.Form):
    studentname = forms.CharField(label='学生姓名', widget=forms.TextInput(attrs={"autocomplete": "off"}))
    studentnum = forms.CharField(label='学号', widget=forms.TextInput(attrs={"autocomplete": "off"}))
    gender = forms.IntegerField(label='性别', widget=forms.RadioSelect(choices=((1, '男',), (0, '女'))))
    idcard = forms.CharField(label='一卡通卡号', widget=forms.TextInput(attrs={"autocomplete": "off"}))
    vm_num = forms.CharField(label='学生机编号', widget=forms.TextInput(attrs={"autocomplete": "off"}), required=False)
    grade = forms.IntegerField(label='班级', widget=forms.Select(), initial='请选择班级')

    def __init__(self, *args, **kwargs):
        super(StudentForm, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self):
        data = self.cleaned_data
        name = data.get("studentname")
        num = data.get("studentnum")
        password = "123456"
        gender = data.get("gender")
        idcard = data.get("idcard")
        grade_id = data.get("grade")
        vm_num = data.get("vm_num")
        if not vm_num:
            vm_num = None
        try:
            Student.objects.get(num=num)
            return {"code": -1, "message": "该学号已存在!"}
        except Exception, e:
            s = Student()
            s.save([name, num, password, idcard, gender, "", vm_num], grade_id)
        return {"code": 1, "message": "ok"}


class StudentEditForm(forms.Form):
    student_id = forms.CharField(label='id', widget=forms.HiddenInput())
    studentname_edit = forms.CharField(label='学生姓名', widget=forms.TextInput(attrs={"autocomplete": "off"}))
    studentnum_edit = forms.CharField(label='学号', widget=forms.TextInput(attrs={"autocomplete": "off"}))
    gender_edit = forms.IntegerField(label='性别', widget=forms.RadioSelect(choices=((1, '男',), (0, '女'))))
    idcard_edit = forms.CharField(label='一卡通卡号', widget=forms.TextInput(attrs={"autocomplete": "off"}))
    vm_number = forms.CharField(label='学生机编号', widget=forms.TextInput(attrs={"autocomplete": "off"}), required=False)
    grade_edit = forms.IntegerField(label='班级', widget=forms.Select(), initial='请选择班级')

    def __init__(self, *args, **kwargs):
        super(StudentEditForm, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self):
        data = self.cleaned_data
        id = data.get("student_id")
        name = data.get("studentname_edit")
        num = data.get("studentnum_edit")
        gender = data.get("gender_edit")
        idcard = data.get("idcard_edit")
        grade_id = data.get("grade_edit")
        vm_num = data.get("vm_number")
        stu = Student.objects.filter(num=num).exclude(id=id)
        if stu:
            return {"code": -1, "message": "该学号已存在!"}
        s = Student.objects.get(id=id)
        password = s.password
        s.save([name, num, password, idcard, gender, "", vm_num], grade_id)
        return {"code": 1, "message": "ok"}


class ChangeStudentPassword(forms.Form):
    password_id = forms.CharField(label='id', widget=forms.HiddenInput())
    new_password = forms.CharField(label='新密码', widget=forms.PasswordInput(attrs={"autocomplete": "off"}))
    re_password = forms.CharField(label='确认密码', widget=forms.PasswordInput(attrs={"autocomplete": "off"}))

    def __init__(self, *args, **kwargs):
        super(ChangeStudentPassword, self).__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self):
        data = self.cleaned_data
        id = data.get("password_id")
        password = data.get("new_password")
        s = Student.objects.get(id=id)
        if not s.stu_vm_number:
            vmnum = None
        else:
            vmnum = int(s.stu_vm_number)
        s.save([s.name, s.num, password, s.idcard, s.gender, "", vmnum], s.grade_id)
        return {"code": 1, "message": "ok"}



