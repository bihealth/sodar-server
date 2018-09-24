from django.conf.urls import url

from . import views


app_name = 'samplesheets.studyapps.cancer'

urlpatterns = [
    url(
        regex=r'^file/(?P<file_type>[a-z]+)/(?P<genericmaterial>[0-9a-f-]+)(\..*)?$',
        view=views.FileRedirectView.as_view(),
        name='file',
    ),
    url(
        regex=r'^render/igv/(?P<genericmaterial>[0-9a-f-]+)(\..*)?$',
        view=views.IGVSessionFileRenderView.as_view(),
        name='igv',
    ),
]
