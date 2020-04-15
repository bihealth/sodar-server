from django.conf.urls import url

from . import views


app_name = 'irodsbackend'

urlpatterns = [
    url(
        regex=r'^api/stats/(?P<project>[0-9a-f-]+)$',
        view=views.IrodsStatisticsAjaxView.as_view(),
        name='stats',
    ),
    url(
        regex=r'^api/stats$',
        view=views.IrodsStatisticsAjaxView.as_view(),
        name='stats',
    ),
    url(
        regex=r'^api/stats/(?P<project>[0-9a-f-]+)$',
        view=views.IrodsStatisticsAjaxView.as_view(),
        name='stats',
    ),
    url(
        regex=r'^api/list/(?P<project>[0-9a-f-]+)$',
        view=views.IrodsObjectListAjaxView.as_view(),
        name='list',
    ),
    url(
        regex=r'^api/list$',
        view=views.IrodsObjectListAjaxView.as_view(),
        name='list',
    ),
]
