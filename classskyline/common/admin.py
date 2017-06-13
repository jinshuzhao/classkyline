from django.contrib import admin
from common.models import Host, BaseImage, CourseImage, DesktopImage, CourseProfile, Course
from common.models import Desktop, Classroom, Network, Option, Terminal


# Register your models here.
@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    pass


@admin.register(BaseImage)
class BaseImageAdmin(admin.ModelAdmin):
    pass


@admin.register(CourseImage)
class CourseImageAdmin(admin.ModelAdmin):
    pass


@admin.register(DesktopImage)
class DesktopImageAdmin(admin.ModelAdmin):
    pass


@admin.register(CourseProfile)
class CourseProfileAdmin(admin.ModelAdmin):
    pass


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    pass


@admin.register(Desktop)
class DesktopAdmin(admin.ModelAdmin):
    pass


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    pass


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    pass


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    pass


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    pass
