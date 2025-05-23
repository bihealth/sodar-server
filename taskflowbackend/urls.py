"""URL patterns for the taskflowbackend app"""

from django.urls import path

from taskflowbackend import views_api


app_name = 'taskflowbackend'

urlpatterns = [
    path(
        route='api/lock/status/<uuid:project>',
        view=views_api.ProjectLockStatusAPIView.as_view(),
        name='api_lock_status',
    )
]
