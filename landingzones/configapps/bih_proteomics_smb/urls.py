from django.conf.urls import url

from . import views


app_name = 'landingzones.configapps.bih_proteomics_smb'

urlpatterns = [
    url(
        regex=r'^(?P<landingzone>[0-9a-f-]+)$',
        view=views.ZoneTicketGetView.as_view(),
        name='ticket_get',
    ),
]
