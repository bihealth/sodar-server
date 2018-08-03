import logging
import rules

from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import Project, RoleAssignment, OMICS_CONSTANTS
from projectroles.plugins import get_backend_api


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']


class BaseIrodsAPIView(
        LoginRequiredMixin, APIView):
    """Base iRODS API View"""

    def __init__(self, *args, **kwargs):
        super(BaseIrodsAPIView, self).__init__(*args, **kwargs)
        self.project = None
        self.irods_backend = get_backend_api('omics_irods')

    def get(self, *args, **kwargs):
        """Setup get() function"""
        if 'project' in self.kwargs:
            try:
                self.project = Project.objects.get(
                    omics_uuid=self.kwargs['project'])

            except Project.DoesNotExist:
                return Response('Project not found', status=400)

        if not self.irods_backend:
            return Response('iRODS backend not enabled', status=500)

        if 'path' not in self.kwargs:
            return Response('Path not set', status=400)

        # Ensure the given path belongs in the project
        if (self.project and
                self.irods_backend.get_path(
                    self.project) not in self.kwargs['path']):
            return Response('Path does not belong to project', status=400)

        # Check site perms
        if (not self.request.user.is_superuser and (
                self.project and not self.request.user.has_perm(
                    'projectroles.view_project', self.project))):
            return Response('User not authorized for project', status=403)

        # Check iRODS perms
        irods_session = self.irods_backend.get_session()

        try:
            coll = irods_session.collections.get(self.kwargs['path'])

        except Exception:
            return Response('Not found', status=404)

        # TODO: Are there cases where we should also check group membership?
        perms = irods_session.permissions.get(coll)

        # Quick fix for issue #324
        owner_or_delegate = False

        if self.project:
            user_as = RoleAssignment.objects.get_assignment(
                self.request.user, self.project)

            if user_as and user_as.role.name in [
                    PROJECT_ROLE_OWNER, PROJECT_ROLE_DELEGATE]:
                owner_or_delegate = True

        if (not self.request.user.is_superuser and
                not owner_or_delegate and
                self.request.user.username not in [p.user_name for p in perms]):
            return Response(
                'User not authorized for iRODS collection', status=403)

        return None     # Better way to do this?


class IrodsStatisticsAPIView(BaseIrodsAPIView):
    """View for returning collection file statistics for the UI"""

    def get(self, *args, **kwargs):
        response = super(IrodsStatisticsAPIView, self).get(*args, **kwargs)

        if response:
            return response

        try:
            stats = self.irods_backend.get_object_stats(self.kwargs['path'])
            return Response(stats, status=200)

        except FileNotFoundError:
            return Response('Not found', status=404)

        except Exception as ex:
            return Response(str(ex), status=500)


class IrodsObjectListAPIView(BaseIrodsAPIView):
    """View for listing data objects in iRODS recursively"""

    def get(self, *args, **kwargs):
        response = super(IrodsObjectListAPIView, self).get(*args, **kwargs)

        if response:
            return response

        # Get files
        try:
            ret_data = self.irods_backend.get_objects(
                self.kwargs['path'], check_md5=bool(int(self.kwargs['md5'])))
            return Response(ret_data, status=200)

        except FileNotFoundError:
            return Response('Not found', status=404)

        except Exception as ex:
            return Response(str(ex), status=500)
