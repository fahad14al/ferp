from django.db import models

class GeneralSettings(models.Model):
    """Global settings for the ERP system"""
    tax_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=15.00,
        help_text="Default tax percentage for sales (e.g., 15.00 for 15%)"
    )
    
    class Meta:
        verbose_name = "General Setting"
        verbose_name_plural = "General Settings"

    def __str__(self):
        return "System Settings"

    def save(self, *args, **kwargs):
        """Ensure only one instance of settings exists"""
        if not self.pk and GeneralSettings.objects.exists():
            # If trying to create a new one but one already exists, 
            # we should technically prevent it or update the existing one.
            # For simplicity, we just don't allow creation if one exists in admin 
            # but we'll also handle it in the admin class.
            return
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get the settings instance or create default one"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
