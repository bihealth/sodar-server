from django.conf.urls import url

from . import views

app_name = 'landingzones'

urlpatterns = [
    # Site views
    url(
        regex=r'^(?P<project>[0-9a-f-]+)$',
        view=views.ProjectZoneView.as_view(),
        name='list',
    ),
    url(
        regex=r'^assay/(?P<assay>[0-9a-f-]+)$',     # TODO: TBD: Is this needed?
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
        regex=r'^delete/(?P<landingzone>[0-9a-f-]+)$',
        view=views.ZoneDeleteView.as_view(),
        name='delete',
    ),
    # Javascript API views
    url(
        regex=r'^status/(?P<landingzone>[0-9a-f-]+)$',
        view=views.LandingZoneStatusGetAPIView.as_view(),
        name='status',
    ),
    url(
        regex=r'^irods/list/(?P<landingzone>[0-9a-f-]+)$',
        view=views.LandingZoneObjectListAPIView.as_view(),
        name='irods_list',
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
    url(
        regex=r'^taskflow/delete$',
        view=views.ZoneDeleteAPIView.as_view(),
        name='taskflow_zone_delete',
    ),
]

'''            

    # Taskflow API views
    url(
        regex=r'^taskflow/zone/delete$',
        view=views.ZoneDeleteAPIView.as_view(),
        name='taskflow_zone_delete',
    ),
    url(
        regex=r'^taskflow/status/get$',
        view=views.ZoneStatusGetAPIView.as_view(),
        name='taskflow_zone_status_get',
    ),
]
'''