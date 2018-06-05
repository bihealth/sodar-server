from django.conf.urls import url

from . import views


app_name = 'samplesheets.configapps.bih_germline'

urlpatterns = [
    url(
        regex=r'^(?P<file_type>[a-z]+)/family/'
              r'(?P<family_id>[\w\-_]+)/(?P<genericmaterial>[0-9a-f-]+)$',
        view=views.FileRedirectView.as_view(),
        name='file',
    ),
]