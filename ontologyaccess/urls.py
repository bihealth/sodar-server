"""URL patterns for the ontologyaccess app"""

from django.conf.urls import url

from ontologyaccess import views, views_ajax


app_name = 'ontologyaccess'

# UI views
urls_ui = [
    url(
        regex=r'^list$',
        view=views.OBOFormatOntologyListView.as_view(),
        name='list',
    ),
    url(
        regex=r'^obo/detail/(?P<oboformatontology>[0-9a-f-]+)$',
        view=views.OBOFormatOntologyDetailView.as_view(),
        name='obo_detail',
    ),
    url(
        regex=r'^obo/import$',
        view=views.OBOFormatOntologyImportView.as_view(),
        name='obo_import',
    ),
    url(
        regex=r'^obo/update/(?P<oboformatontology>[0-9a-f-]+)$',
        view=views.OBOFormatOntologyUpdateView.as_view(),
        name='obo_update',
    ),
    url(
        regex=r'^obo/delete/(?P<oboformatontology>[0-9a-f-]+)$',
        view=views.OBOFormatOntologyDeleteView.as_view(),
        name='obo_delete',
    ),
]

# Ajax API views
urls_ajax = [
    url(
        regex=r'^ajax/obo/list$',
        view=views_ajax.OBOOntologyListAjaxView.as_view(),
        name='ajax_obo_list',
    ),
    url(
        regex=r'^ajax/obo/term/query$',
        view=views_ajax.OBOTermQueryAjaxView.as_view(),
        name='ajax_obo_term_query',
    ),
    url(
        regex=r'^ajax/obo/term/query/(?P<oboformatontology>[0-9a-f-]+)$',
        view=views_ajax.OBOTermQueryAjaxView.as_view(),
        name='ajax_obo_term_query',
    ),
]

urlpatterns = urls_ui + urls_ajax
