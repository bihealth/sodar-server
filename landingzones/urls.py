from django.conf.urls import url

from landingzones import views

app_name = 'landingzones'

urlpatterns = [
    # Site views
    url(
        regex=r'^(?P<project>[0-9a-f-]+)$',
        view=views.ProjectZoneView.as_view(),
        name='list',
    ),
    url(
        regex=r'^create/(?P<project>[0-9a-f-]+)$',
        view=views.ZoneCreateView.as_view(),
        name='create',
    ),
    url(
        regex=r'^move/(?P<landingzone>[0-9a-f-]+)$',
        view=views.ZoneMoveView.as_view(),
        name='move',
    ),
    url(
        regex=r'^validate/(?P<landingzone>[0-9a-f-]+)$',
        view=views.ZoneMoveView.as_view(),
        name='validate',
    ),
    url(
        regex=r'^delete/(?P<landingzone>[0-9a-f-]+)$',
        view=views.ZoneDeleteView.as_view(),
        name='delete',
    ),
    url(
        regex=r'^clear/(?P<project>[0-9a-f-]+)$',
        view=views.ZoneClearView.as_view(),
        name='clear',
    ),
    # General API views
    # TODO: Refactor urls to have e.g. /api/ in them
    url(
        regex=r'^api/list/(?P<configuration>[\w\-_/]+)$',
        view=views.LandingZoneListAPIView.as_view(),
        name='api_list',
    ),
    url(
        regex=r'^status/(?P<landingzone>[0-9a-f-]+)$',
        view=views.LandingZoneStatusGetAPIView.as_view(),
        name='status',
    ),
    # Taskflow API views
    url(
        regex=r'^taskflow/create$',
        view=views.ZoneCreateAPIView.as_view(),
        name='taskflow_zone_create',
    ),
    url(
        regex=r'^taskflow/status/set$',
        view=views.ZoneStatusSetAPIView.as_view(),
        name='taskflow_zone_status_set',
    ),
]
