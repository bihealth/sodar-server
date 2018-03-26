from django.conf.urls import url

from . import views


app_name = 'timeline'

urlpatterns = [
    url(
        regex=r'^(?P<project>[0-9a-f-]+)$',
        view=views.ProjectTimelineView.as_view(),
        name='project_timeline',
    ),
    url(
        regex=r'^(?P<project>[0-9a-f-]+)/(?P<object_model>[\w-]+)/'
              r'(?P<object_uuid>[\w-]+)$',
        view=views.ObjectTimelineView.as_view(),
        name='object_timeline',
    ),
    # Taskflow API views
    url(
        regex=r'^taskflow/status/set$',
        view=views.TimelineEventStatusSetAPIView.as_view(),
        name='taskflow_timeline_event_status_set',
    ),
]
