"""URL patterns for the isatemplates app"""

from django.urls import path

from isatemplates import views

app_name = 'isatemplates'

urlpatterns = [
    path(
        route='list',
        view=views.ISATemplateListView.as_view(),
        name='list',
    ),
    path(
        route='<uuid:cookiecutterisatemplate>',
        view=views.ISATemplateDetailView.as_view(),
        name='detail',
    ),
    path(
        route='cubi/<str:name>',
        view=views.CUBIISATemplateDetailView.as_view(),
        name='detail_cubi',
    ),
    path(
        route='create',
        view=views.ISATemplateCreateView.as_view(),
        name='create',
    ),
    path(
        route='update/<uuid:cookiecutterisatemplate>',
        view=views.ISATemplateUpdateView.as_view(),
        name='update',
    ),
    path(
        route='delete/<uuid:cookiecutterisatemplate>',
        view=views.ISATemplateDeleteView.as_view(),
        name='delete',
    ),
    path(
        route='export/<uuid:cookiecutterisatemplate>',
        view=views.ISATemplateExportView.as_view(),
        name='export',
    ),
]
