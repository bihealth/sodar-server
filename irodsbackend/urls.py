from django.conf.urls import url

from . import views


app_name = 'irodsbackend'

urlpatterns = [
    url(
        regex=r'^api/stats/(?P<project>[0-9a-f-]+)\?path=(?P<path>[\w\-_/@]+)$',
        view=views.IrodsStatisticsAPIView.as_view(),
        name='stats',
    ),
    url(
        regex=r'^api/stats\?path=(?P<path>[\w\-_/@]+)$',
        view=views.IrodsStatisticsAPIView.as_view(),
        name='stats',
    ),
    url(
        regex=r'^api/list/(?P<project>[0-9a-f-]+)\?path=(?P<path>[\w\-_/@]+)&md5=(?P<md5>[01])$',
        view=views.IrodsObjectListAPIView.as_view(),
        name='list',
    ),
    url(
        regex=r'^api/list\?path=(?P<path>[\w\-_/@]+)&md5=(?P<md5>[01])$',
        view=views.IrodsObjectListAPIView.as_view(),
        name='list',
    ),
]
