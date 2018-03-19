from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views import defaults as default_views
from django.views.generic import TemplateView

from projectroles.views import HomeView

# from djangoplugins.utils import include_plugins
# from projectroles.plugins import ProjectAppPluginPoint

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^about/$', TemplateView.as_view(template_name='pages/about.html'),
        name='about'),

    # Django Admin, use {% url 'admin:index' %}
    url(settings.ADMIN_URL, admin.site.urls),

    # User management
    url(r'^users/', include('omics_data_mgmt.users.urls', namespace='users')),

    # Login and logout
    url(r'^login/$', auth_views.login, name='account_login'),
    url(r'^logout/$', auth_views.logout_then_login, name='account_logout'),

    # General site apps
    url(r'^alerts/', include('adminalerts.urls')),

    # Projectroles URLs
    url(r'^projects/', include('projectroles.urls')),

    # App plugin URLs
    # TODO: Test if this can be made to work on Flynn and without the extra
    # TODO:     "plugin" kwarg for the API view classes
    # url(r'^', include_plugins(ProjectAppPluginPoint)),
    url(r'^timeline/', include('timeline.urls')),
    url(r'^files/', include('filesfolders.urls')),
    url(r'^samplesheets/', include('samplesheets.urls')),

    # django-db-file-storage URLs (needed for admin, obfuscated for users)
    url(r'^xu7in5zs9lylar0n/', include('db_file_storage.urls')),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        url(r'^400/$', default_views.bad_request,
            kwargs={'exception': Exception('Bad Request!')}),
        url(r'^403/$', default_views.permission_denied,
            kwargs={'exception': Exception('Permission Denied')}),
        url(r'^404/$', default_views.page_not_found,
            kwargs={'exception': Exception('Page not Found')}),
        url(r'^500/$', default_views.server_error),
    ]
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
