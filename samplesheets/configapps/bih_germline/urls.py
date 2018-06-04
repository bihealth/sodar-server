from django.conf.urls import url

from . import views


app_name = 'samplesheets.configapps.bih_germline'

urlpatterns = [
    url(
        regex=r'^bam/(?P<genericmaterial>[0-9a-f-]+)$',
        view=views.BamFileRedirectView.as_view(),
        name='bam',
    ),
]