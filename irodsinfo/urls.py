from django.conf.urls import url

from . import views

app_name = 'irodsinfo'

urlpatterns = [
    url(
        regex=r'^info$',
        view=views.IrodsInfoView.as_view(),
        name='info'),
    url(
        regex=r'^config$',
        view=views.IrodsConfigView.as_view(),
        name='config'),
]
