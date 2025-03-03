from django.urls import path

from . import views


app_name = 'landingzones.configapps.bih_proteomics_smb'

urlpatterns = [
    path(
        route='<uuid:landingzone>',
        view=views.ZoneTicketGetView.as_view(),
        name='ticket_get',
    )
]
