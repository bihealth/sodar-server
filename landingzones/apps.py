from django.apps import AppConfig


class LandingzonesConfig(AppConfig):
    name = 'landingzones'

    def ready(self):
        import landingzones.checks  # noqa
