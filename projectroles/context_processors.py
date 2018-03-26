from .urls import urlpatterns


def urls_processor(request):
    """Context processor for providing projectroles URLs for the sidebar"""
    # NOTE: We must do this in a context processor, as including urls in
    #       views.py produces a cyclic dependency
    return {
        'projectroles_urls': urlpatterns,
        'role_urls': [
            'roles',
            'role_create',
            'role_update',
            'role_delete',
            'invites',
            'invite_create',
            'invite_resend',
            'invite_revoke']}
