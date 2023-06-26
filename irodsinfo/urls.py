"""URL patterns for the irodsinfo app"""

from django.urls import path

from irodsinfo import views, views_api

app_name = 'irodsinfo'

# UI views
urls_ui = [
    path(
        route='info',
        view=views.IrodsInfoView.as_view(),
        name='info',
    ),
    path(
        route='config',
        view=views.IrodsConfigView.as_view(),
        name='config',
    ),
]

# REST API views
urls_api = [
    path(
        route='api/environment',
        view=views_api.IrodsEnvRetrieveAPIView.as_view(),
        name='api_env',
    ),
]

urlpatterns = urls_ui + urls_api
