from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^(?P<project>\d+)$',
        view=views.ProjectSheetsView.as_view(),
        name='project_sheets',
    ),
]
