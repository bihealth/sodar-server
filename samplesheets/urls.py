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
    # Ajax API views
    url(
        regex=r'^api/context/get/(?P<project>[0-9a-f-]+)$',
        view=views.SampleSheetContextGetAPIView.as_view(),
        name='api_context_get',
    ),
    url(
        regex=r'^api/study/tables/get/(?P<study>[0-9a-f-]+)$',
        view=views.SampleSheetStudyTablesGetAPIView.as_view(),
        name='api_study_tables_get',
    ),
    url(
        regex=r'^api/study/links/get/(?P<study>[0-9a-f-]+)$',
        view=views.SampleSheetStudyLinksGetAPIView.as_view(),
        name='api_study_links_get',
    ),
    # General API views
    url(
        regex=r'^api/source/get/(?P<source_id>[\w\-_/]+)$',
        view=views.SourceIDQueryAPIView.as_view(),
        name='source_get',
    ),
    # Taskflow API views
    url(
        regex=r'^taskflow/dirs/get$',
        view=views.TaskflowDirStatusGetAPIView.as_view(),
        name='taskflow_sheet_dirs_get',
    ),
    url(
        regex=r'^taskflow/dirs/set$',
        view=views.TaskflowDirStatusSetAPIView.as_view(),
        name='taskflow_sheet_dirs_set',
    ),
    url(
        regex=r'^taskflow/delete$',
        view=views.TaskflowSheetDeleteAPIView.as_view(),
        name='taskflow_sheet_delete',
    ),
]
