from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.shortcuts import render
from django.views import defaults as default_views
from django.views.generic import TemplateView

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
    url(r'^$', HomeView.as_view(), name='home'),
    # Django Admin, use {% url 'admin:index' %}
    url(settings.ADMIN_URL, admin.site.urls),
    # Login and logout
    url(
        r'^login/$',
        auth_views.LoginView.as_view(template_name='users/login.html'),
        name='login',
    ),
    url(r'^logout/$', auth_views.logout_then_login, name='logout'),
    # User Profile URLs
    url(r'^user/', include('userprofile.urls')),
    # Auth
    url(r'api/auth/', include('knox.urls')),
    # Iconify SVG icons
    url(r'icons/', include('dj_iconify.urls')),
    # General site apps
    url(r'^alerts/adm/', include('adminalerts.urls')),
    url(r'^alerts/app/', include('appalerts.urls')),
    url(r'^siteinfo/', include('siteinfo.urls')),
    url(r'^irods/', include('irodsinfo.urls')),
    url(r'^tokens/', include('tokens.urls')),
    url(r'^ontology/', include('ontologyaccess.urls')),
    # Projectroles URLs
    url(r'^project/', include('projectroles.urls')),
    # App plugin URLs
    # TODO: See if plugin URLs can be made to work now (Flynn no longer used)
    # url(r'^', include_plugins(ProjectAppPluginPoint)),
    url(r'^timeline/', include('timeline.urls')),
    url(r'^samplesheets/', include('samplesheets.urls')),
    url(r'^landingzones/', include('landingzones.urls')),
    # Backend apps with API URLs
    url(r'^irodsbackend/', include('irodsbackend.urls')),
    # Samplesheets study sub-app URLs
    url(
        r'^samplesheets/study/germline/',
        include('samplesheets.studyapps.germline.urls'),
    ),
    url(
        r'^samplesheets/study/cancer/',
        include('samplesheets.studyapps.cancer.urls'),
    ),
    # Landingzones config sub-app URLs
    url(
        r'^landingzones/config/bih-proteomics-smb/',
        include('landingzones.configapps.bih_proteomics_smb.urls'),
    ),
    # Sodarcache URLs
    url(r'^cache/', include('sodarcache.urls')),
    # The rendered Sphinx-based manual.
    url(r'^manual/', include('docs.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        url(
            r'^400/$',
            default_views.bad_request,
            kwargs={'exception': Exception('Bad Request!')},
        ),
        url(
            r'^403/$',
            default_views.permission_denied,
            kwargs={'exception': Exception('Permission Denied')},
        ),
        url(
            r'^404/$',
            default_views.page_not_found,
            kwargs={'exception': Exception('Page not Found')},
        ),
        url(r'^500/$', default_views.server_error),
    ]

    urlpatterns += staticfiles_urlpatterns()

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls))
        ] + urlpatterns
