from django.contrib import admin
from users import models


@admin.register(models.Profile)
class DefaultAdmin(admin.ModelAdmin):
    pass
