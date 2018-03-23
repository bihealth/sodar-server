from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^(?P<project>[\w-]+)$',
        view=views.ProjectSheetsView.as_view(),
        name='project_sheets',
    ),
    url(
        regex=r'^(?P<project>[\w-]+)/study/(?P<study>[\w-]+)$',
        view=views.ProjectSheetsView.as_view(),
        name='project_sheets',
    ),
    url(
        regex=r'^(?P<project>[\w-]+)/meta/(?P<subpage>[\w-]+)$',
        view=views.ProjectSheetsView.as_view(),
        name='project_sheets',
    ),
    url(
        regex=r'^(?P<project>[\w-]+)/import$',
        view=views.SampleSheetImportView.as_view(),
        name='sheet_import',
    ),
    url(
        regex=r'^(?P<project>[\w-]+)/delete$',
        view=views.SampleSheetDeleteView.as_view(),
        name='sheet_delete',
    ),
]
