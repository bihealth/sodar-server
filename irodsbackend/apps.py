from django.apps import AppConfig


class IrodsbackendConfig(AppConfig):
    name = 'irodsbackend'

    def ready(self):
        import irodsbackend.checks  # noqa
        import irodsbackend.signals  # noqa
