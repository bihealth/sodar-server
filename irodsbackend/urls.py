from django.conf.urls import url

from . import views


app_name = 'irodsbackend'

urlpatterns = [
    url(
        regex=r'^ajax/stats/(?P<project>[0-9a-f-]+)$',
        view=views.IrodsStatisticsAjaxView.as_view(),
        name='stats',
    ),
    url(
        regex=r'^ajax/list/(?P<project>[0-9a-f-]+)$',
        view=views.IrodsObjectListAjaxView.as_view(),
        name='list',
    ),
    url(
        regex=r'^api/auth$',
        view=views.LocalAuthAPIView.as_view(),
        name='api_auth',
    ),
]
