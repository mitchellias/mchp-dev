from django.contrib import admin
from . import models


@admin.register(models.Roster)
class RosterAdmin(admin.ModelAdmin):
    list_display = ('course', 'created_by', 'when')
    fieldsets = (
        (None, {
            'fields': ['course', 'html'],
        }),
        ('Personal information', {
            'fields': ['created_by'],
        }),
        ('Important dates', {
            'fields': ['when'],
        })
    )
