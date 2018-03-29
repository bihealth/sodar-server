from django.conf.urls import url

from . import views

app_name = 'adminalerts'

urlpatterns = [
    url(
        regex=r'^list$',
        view=views.AdminAlertListView.as_view(),
        name='list'),
    url(
        regex=r'^detail/(?P<uuid>[0-9a-f-]+)$',
        view=views.AdminAlertDetailView.as_view(),
        name='detail',
    ),
    url(
        regex=r'^create$',
        view=views.AdminAlertCreateView.as_view(),
        name='create'),
    url(
        regex=r'^update/(?P<uuid>[0-9a-f-]+)$',
        view=views.AdminAlertUpdateView.as_view(),
        name='update',
    ),
    url(
        regex=r'^delete/(?P<uuid>[0-9a-f-]+)/delete',
        view=views.AdminAlertDeleteView.as_view(),
        name='delete',
    ),
]
