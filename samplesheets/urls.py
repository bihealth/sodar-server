from django.conf.urls import url

from . import views


app_name = 'samplesheets'

urlpatterns = [
    url(
        regex=r'^(?P<project>[0-9a-f-]+)$',
        view=views.ProjectSheetsView.as_view(),
        name='project_sheets',
    ),
    url(
        regex=r'^study/(?P<study>[0-9a-f-]+)$',
        view=views.ProjectSheetsView.as_view(),
        name='project_sheets',
    ),
    url(
        regex=r'^overview/(?P<project>[0-9a-f-]+)$',
        view=views.ProjectSheetsOverviewView.as_view(),
        name='overview',
    ),
    url(
        regex=r'^import/(?P<project>[0-9a-f-]+)$',
        view=views.SampleSheetImportView.as_view(),
        name='import',
    ),
    url(
        regex=r'^export/study/(?P<study>[0-9a-f-]+)$',
        view=views.SampleSheetTableExportView.as_view(),
        name='export_tsv',
    ),
    url(
        regex=r'^export/assay/(?P<assay>[0-9a-f-]+)$',
        view=views.SampleSheetTableExportView.as_view(),
        name='export_tsv',
    ),
    url(
        regex=r'^delete/(?P<project>[0-9a-f-]+)$',
        view=views.SampleSheetDeleteView.as_view(),
        name='delete',
    ),
]
