from django.conf.urls import url

from . import views

# NOTES:
# - file/folder/hyperlink objects can be referred to as "item", but only if
#   ObjectPermissionMixin is used in the view


app_name = 'filesfolders'

urlpatterns = [
    url(
        regex=r'^(?P<project>[0-9a-f-]+)$',
        view=views.ProjectFileView.as_view(),
        name='project_files',
    ),
    url(
        regex=r'^folder/(?P<folder>[0-9a-f-]+)$',
        view=views.ProjectFileView.as_view(),
        name='project_files',
    ),
    url(
        regex=r'^upload/(?P<project>[0-9a-f-]+)$',
        view=views.FileCreateView.as_view(),
        name='file_create',
    ),
    url(
        regex=r'^upload/in/(?P<folder>[0-9a-f-]+)$',
        view=views.FileCreateView.as_view(),
        name='file_create',
    ),
    url(
        regex=r'^update/(?P<item>[0-9a-f-]+)$',
        view=views.FileUpdateView.as_view(),
        name='file_update',
    ),
    url(
        regex=r'^delete/(?P<item>[0-9a-f-]+)$',
        view=views.FileDeleteView.as_view(),
        name='file_delete',
    ),
    url(
        regex=r'^download/(?P<file>[0-9a-f-]+)/(?P<file_name>[^\0/]+)$',
        view=views.FileServeView.as_view(),
        name='file_serve',
    ),
    url(
        regex=r'^download/(?P<secret>[\w\-]+)/(?P<file_name>[^\0/]+)$',
        view=views.FileServePublicView.as_view(),
        name='file_serve_public',
    ),
    url(
        regex=r'^link/(?P<file>[0-9a-f-]+)$',
        view=views.FilePublicLinkView.as_view(),
        name='file_public_link',
    ),
    url(
        regex=r'^folder/add/(?P<project>[0-9a-f-]+)$',
        view=views.FolderCreateView.as_view(),
        name='folder_create',
    ),
    url(
        regex=r'^folder/add/in/(?P<folder>[0-9a-f-]+)$',
        view=views.FolderCreateView.as_view(),
        name='folder_create',
    ),
    url(
        regex=r'^folder/update/(?P<item>[0-9a-f-]+)$',
        view=views.FolderUpdateView.as_view(),
        name='folder_update',
    ),
    url(
        regex=r'^folder/delete(?P<item>[0-9a-f-]+)$',
        view=views.FolderDeleteView.as_view(),
        name='folder_delete',
    ),
    url(
        regex=r'^link/add/(?P<project>[0-9a-f-]+)$',
        view=views.HyperLinkCreateView.as_view(),
        name='hyperlink_create',
    ),
    url(
        regex=r'^link/add/in/(?P<folder>[0-9a-f-]+)$',
        view=views.HyperLinkCreateView.as_view(),
        name='hyperlink_create',
    ),
    url(
        regex=r'^link/update/(?P<item>[0-9a-f-]+)$',
        view=views.HyperLinkUpdateView.as_view(),
        name='hyperlink_update',
    ),
    url(
        regex=r'^link/delete/(?P<item>[0-9a-f-]+)$',
        view=views.HyperLinkDeleteView.as_view(),
        name='hyperlink_delete',
    ),
    url(
        regex=r'^batch/(?P<project>[0-9a-f-]+)$',
        view=views.BatchEditView.as_view(),
        name='batch_edit',
    ),
    url(
        regex=r'^batch/(?P<folder>[0-9a-f-]+)$',
        view=views.BatchEditView.as_view(),
        name='batch_edit',
    ),
]
