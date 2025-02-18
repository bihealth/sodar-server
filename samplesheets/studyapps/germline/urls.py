from django.urls import re_path

from . import views


app_name = 'samplesheets.studyapps.germline'

urlpatterns = [
    re_path(
        route=r'^render/igv/(?P<genericmaterial>[0-9a-f-]+)(\..*)?$',
        view=views.IGVSessionFileRenderView.as_view(),
        name='igv',
    )
]
