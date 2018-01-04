from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^list$',
        view=views.AdminAlertListView.as_view(),
        name='alert_list'),
    url(
        regex=r'^(?P<pk>\d+)$',
        view=views.AdminAlertDetailView.as_view(),
        name='alert_detail',
    ),
    url(
        regex=r'^create$',
        view=views.AdminAlertCreateView.as_view(),
        name='alert_create'),
    url(
        regex=r'^(?P<pk>\d+)/update$',
        view=views.AdminAlertUpdateView.as_view(),
        name='alert_update',
    ),
    url(
        regex=r'^(?P<pk>\d+)/delete$',
        view=views.AdminAlertDeleteView.as_view(),
        name='alert_delete',
    ),
]
