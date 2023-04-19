from django.urls import path

from . import views

urlpatterns = [
    path(
        route='',
        view=views.UserListView.as_view(),
        name='user_list',
    ),
    path(
        route='<str:username>/',
        view=views.UserDetailView.as_view(),
        name='user_detail',
    ),
]
