from django.urls import path

from . import views

app_name = 'irodsinfo'

urlpatterns = [
    path(
        route='info',
        view=views.IrodsInfoView.as_view(),
        name='info',
    ),
    path(
        route='config',
        view=views.IrodsConfigView.as_view(),
        name='config',
    ),
]
