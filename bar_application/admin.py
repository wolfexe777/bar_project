from django.contrib import admin

from . models import UserProfile, JobProfile

@admin.register(UserProfile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('external_id', 'phone_number')

@admin.register(JobProfile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('external_id', 'phone_number')
