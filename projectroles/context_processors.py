from .urls import urlpatterns


def urls_processor(request):
    """Context processor for providing projectroles URLs for the sidebar"""
    # NOTE: We must do this in a context processor, as including urls in
    #       views.py produces a cyclic dependency
    return {
        'projectroles_urls': urlpatterns,
        'role_urls': [
            'project_roles',
            'role_create',
            'role_update',
            'role_delete',
            'role_invites',
            'role_invite_create',
            'role_invite_resend',
            'role_invite_revoke']}
