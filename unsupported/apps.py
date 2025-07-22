from django.apps import AppConfig


class UnsupportedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'unsupported'
