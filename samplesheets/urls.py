from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^(?P<project>\d+)$',
        view=views.ProjectSheetsView.as_view(),
        name='project_sheets',
    ),
    url(
        regex=r'^(?P<project>\d+)/study/(?P<study>\d+)$',
        view=views.ProjectSheetsView.as_view(),
        name='project_sheets',
    ),
    url(
        regex=r'^(?P<project>\d+)/meta/(?P<subpage>[^\0]{0,256})$',
        view=views.ProjectSheetsView.as_view(),
        name='project_sheets',
    ),
    url(
        regex=r'^(?P<project>\d+)/import$',
        view=views.SampleSheetImportView.as_view(),
        name='sheet_import',
    ),
    url(
        regex=r'^(?P<project>\d+)/delete$',
        view=views.SampleSheetDeleteView.as_view(),
        name='sheet_delete',
    ),
]
