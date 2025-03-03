from django.urls import path

from . import views


app_name = 'irodsbackend'

urlpatterns = [
    path(
        route='ajax/stats/<uuid:project>',
        view=views.IrodsStatisticsAjaxView.as_view(),
        name='stats',
    ),
    path(
        route='ajax/list/<uuid:project>',
        view=views.IrodsObjectListAjaxView.as_view(),
        name='list',
    ),
    # NOTE: Not exactly REST API view, but URL maintained for backwards comp
    path(
        route='api/auth',
        view=views.BasicAuthView.as_view(),
        name='api_auth',
    ),
]
