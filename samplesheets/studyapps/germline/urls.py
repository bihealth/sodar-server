from django.urls import path

from . import views


app_name = 'samplesheets.studyapps.germline'

urlpatterns = [
    path(
        route='render/igv/<uuid:genericmaterial>',
        view=views.IGVSessionFileRenderView.as_view(),
        name='igv',
    )
]
