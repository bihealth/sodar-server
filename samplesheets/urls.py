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
        regex=r'^dirs/(?P<project>[0-9a-f-]+)$',
        view=views.IrodsDirsView.as_view(),
        name='dirs',
    ),
    url(
        regex=r'^delete/(?P<project>[0-9a-f-]+)$',
        view=views.SampleSheetDeleteView.as_view(),
        name='delete',
    ),
    # Javascript API views
    url(
        regex=r'^irods/list/assay/(?P<assay>[0-9a-f-]+)?path=(?P<path>[\w\-_/]+)$',
        view=views.IrodsObjectListAPIView.as_view(),
        name='irods_list',
    ),
    # Taskflow API views
    url(
        regex=r'^taskflow/dirs/get$',
        view=views.SampleSheetDirStatusGetAPIView.as_view(),
        name='taskflow_sheet_dirs_get',
    ),
    url(
        regex=r'^taskflow/dirs/set$',
        view=views.SampleSheetDirStatusSetAPIView.as_view(),
        name='taskflow_sheet_dirs_set',
    ),
    url(
        regex=r'^taskflow/delete$',
        view=views.SampleSheetDeleteAPIView.as_view(),
        name='taskflow_sheet_delete',
    ),
]
