from django.conf.urls import url

from landingzones import views, views_api, views_ajax

app_name = 'landingzones'

# UI views
urls_ui = [
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
]

# REST API views
urls_api = [
    url(
        regex=r'^api/list/(?P<project>[0-9a-f-]+)',
        view=views_api.ZoneListAPIView.as_view(),
        name='api_list',
    ),
    url(
        regex=r'^api/retrieve/(?P<landingzone>[0-9a-f-]+)',
        view=views_api.ZoneRetrieveAPIView.as_view(),
        name='api_retrieve',
    ),
    url(
        regex=r'^api/create/(?P<project>[0-9a-f-]+)',
        view=views_api.ZoneCreateAPIView.as_view(),
        name='api_create',
    ),
    url(
        regex=r'^api/submit/delete/(?P<landingzone>[0-9a-f-]+)',
        view=views_api.ZoneSubmitDeleteAPIView.as_view(),
        name='api_submit_delete',
    ),
    url(
        regex=r'^api/submit/validate/(?P<landingzone>[0-9a-f-]+)',
        view=views_api.ZoneSubmitMoveAPIView.as_view(),
        name='api_submit_validate',
    ),
    url(
        regex=r'^api/submit/move/(?P<landingzone>[0-9a-f-]+)',
        view=views_api.ZoneSubmitMoveAPIView.as_view(),
        name='api_submit_move',
    ),
    url(
        regex=r'^api/legacy/list/(?P<configuration>[\w\-_/]+)$',
        view=views_api.LandingZoneOldListAPIView.as_view(),
        name='api_list_old',
    ),
]

# Ajax API views
urls_ajax = [
    url(
        regex=r'^ajax/status/retrieve/(?P<landingzone>[0-9a-f-]+)$',
        view=views_ajax.ZoneStatusRetrieveAjaxView.as_view(),
        name='ajax_status',
    )
]

urlpatterns = urls_ui + urls_api + urls_ajax
