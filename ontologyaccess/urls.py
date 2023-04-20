"""URL patterns for the ontologyaccess app"""

from django.urls import path

from ontologyaccess import views, views_ajax


app_name = 'ontologyaccess'

# UI views
urls_ui = [
    path(
        route='list',
        view=views.OBOFormatOntologyListView.as_view(),
        name='list',
    ),
    path(
        route='obo/detail/<uuid:oboformatontology>',
        view=views.OBOFormatOntologyDetailView.as_view(),
        name='obo_detail',
    ),
    path(
        route='obo/import',
        view=views.OBOFormatOntologyImportView.as_view(),
        name='obo_import',
    ),
    path(
        route='obo/update/<uuid:oboformatontology>',
        view=views.OBOFormatOntologyUpdateView.as_view(),
        name='obo_update',
    ),
    path(
        route='obo/delete/<uuid:oboformatontology>',
        view=views.OBOFormatOntologyDeleteView.as_view(),
        name='obo_delete',
    ),
]

# Ajax API views
urls_ajax = [
    path(
        route='ajax/obo/list',
        view=views_ajax.OBOOntologyListAjaxView.as_view(),
        name='ajax_obo_list',
    ),
    path(
        route='ajax/obo/term/query',
        view=views_ajax.OBOTermQueryAjaxView.as_view(),
        name='ajax_obo_term_query',
    ),
    path(
        route='ajax/obo/term/list',
        view=views_ajax.OBOTermListAjaxView.as_view(),
        name='ajax_obo_term_list',
    ),
]

urlpatterns = urls_ui + urls_ajax
