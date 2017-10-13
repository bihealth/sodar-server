from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^(?P<project>\d+)$',
        view=views.ProjectTimelineView.as_view(),
        name='project_timeline',
    ),
    # Taskflow API views
    url(
        regex=r'^taskflow/status/set$',
        view=views.TimelineEventStatusSetAPIView.as_view(),
        name='taskflow_timeline_event_status_set',
    ),
]
