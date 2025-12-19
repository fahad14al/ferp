from django.contrib import admin

# Register your models here.
from .models import GeneralSettings

@admin.register(GeneralSettings)
class GeneralSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Allow adding if no instance exists
        return not GeneralSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False

    list_display = ('__str__', 'tax_percent')
