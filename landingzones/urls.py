"""URL patterns for the landingzones app"""

from django.urls import path

from landingzones import views, views_api, views_ajax

app_name = 'landingzones'

# UI views
urls_ui = [
    path(
        route='<uuid:project>',
        view=views.ProjectZoneView.as_view(),
        name='list',
    ),
    path(
        route='create/<uuid:project>',
        view=views.ZoneCreateView.as_view(),
        name='create',
    ),
    path(
        route='update/<uuid:landingzone>',
        view=views.ZoneUpdateView.as_view(),
        name='update',
    ),
    path(
        route='move/<uuid:landingzone>',
        view=views.ZoneMoveView.as_view(),
        name='move',
    ),
    path(
        route='validate/<uuid:landingzone>',
        view=views.ZoneMoveView.as_view(),
        name='validate',
    ),
    path(
        route='delete/<uuid:landingzone>',
        view=views.ZoneDeleteView.as_view(),
        name='delete',
    ),
]

# REST API views
urls_api = [
    path(
        route='api/list/<uuid:project>',
        view=views_api.ZoneListAPIView.as_view(),
        name='api_list',
    ),
    path(
        route='api/retrieve/<uuid:landingzone>',
        view=views_api.ZoneRetrieveAPIView.as_view(),
        name='api_retrieve',
    ),
    path(
        route='api/create/<uuid:project>',
        view=views_api.ZoneCreateAPIView.as_view(),
        name='api_create',
    ),
    path(
        route='api/update/<uuid:landingzone>',
        view=views_api.ZoneUpdateAPIView.as_view(),
        name='api_update',
    ),
    path(
        route='api/submit/delete/<uuid:landingzone>',
        view=views_api.ZoneSubmitDeleteAPIView.as_view(),
        name='api_submit_delete',
    ),
    path(
        route='api/submit/validate/<uuid:landingzone>',
        view=views_api.ZoneSubmitMoveAPIView.as_view(),
        name='api_submit_validate',
    ),
    path(
        route='api/submit/move/<uuid:landingzone>',
        view=views_api.ZoneSubmitMoveAPIView.as_view(),
        name='api_submit_move',
    ),
]

# Ajax API views
urls_ajax = [
    path(
        route='ajax/status/retrieve/<uuid:landingzone>',
        view=views_ajax.ZoneStatusRetrieveAjaxView.as_view(),
        name='ajax_status',
    )
]

urlpatterns = urls_ui + urls_api + urls_ajax
