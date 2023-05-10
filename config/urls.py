from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.shortcuts import render
from django.urls import path
from django.views import defaults as default_views

from projectroles.views import HomeView


if settings.ENABLE_SENTRY and not settings.DEBUG:
    from sentry_sdk import last_event_id

    def handler500(request, *args, **argv):
        return render(
            request,
            '500.html',
            {'sentry_event_id': last_event_id()},
            status=500,
        )


urlpatterns = [
    path(route='', view=HomeView.as_view(), name='home'),
    # Django Admin, use {% url 'admin:index' %}
    url(settings.ADMIN_URL, admin.site.urls),
    # Login and logout
    path(
        route='login/',
        view=auth_views.LoginView.as_view(template_name='users/login.html'),
        name='login',
    ),
    path(
        route='logout/',
        view=auth_views.logout_then_login,
        name='logout',
    ),
    # User Profile URLs
    path('user/', include('userprofile.urls')),
    # Auth
    path('api/auth/', include('knox.urls')),
    # Iconify SVG icons
    path('icons/', include('dj_iconify.urls')),
    # General site apps
    path('alerts/adm/', include('adminalerts.urls')),
    path('alerts/app/', include('appalerts.urls')),
    path('siteinfo/', include('siteinfo.urls')),
    path('irods/', include('irodsinfo.urls')),
    path('tokens/', include('tokens.urls')),
    path('ontology/', include('ontologyaccess.urls')),
    # Projectroles URLs
    path('project/', include('projectroles.urls')),
    # App plugin URLs
    # TODO: See if plugin URLs can be made to work now (Flynn no longer used)
    # url(r'^', include_plugins(ProjectAppPluginPoint)),
    path('timeline/', include('timeline.urls')),
    path('samplesheets/', include('samplesheets.urls')),
    path('landingzones/', include('landingzones.urls')),
    # Backend apps with API URLs
    path('irodsbackend/', include('irodsbackend.urls')),
    # Samplesheets study sub-app URLs
    path(
        'samplesheets/study/germline/',
        include('samplesheets.studyapps.germline.urls'),
    ),
    path(
        'samplesheets/study/cancer/',
        include('samplesheets.studyapps.cancer.urls'),
    ),
    # Landingzones config sub-app URLs
    path(
        'landingzones/config/bih-proteomics-smb/',
        include('landingzones.configapps.bih_proteomics_smb.urls'),
    ),
    # Sodarcache URLs
    path('cache/', include('sodarcache.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            route='400/',
            view=default_views.bad_request,
            kwargs={'exception': Exception('Bad Request!')},
        ),
        path(
            route='403/',
            view=default_views.permission_denied,
            kwargs={'exception': Exception('Permission Denied')},
        ),
        path(
            route='404/',
            view=default_views.page_not_found,
            kwargs={'exception': Exception('Page not Found')},
        ),
        path(route='500/', view=default_views.server_error),
    ]

    urlpatterns += staticfiles_urlpatterns()

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls))
        ] + urlpatterns
