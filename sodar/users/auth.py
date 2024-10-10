"""
Module for using HTTP Auth Basic login if user is not already authenticated via
Django session.
"""

import base64

from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.utils.decorators import method_decorator, decorator_from_middleware
from django.utils.deprecation import MiddlewareMixin

from knox.auth import TokenAuthentication


class FallbackToAuthBasicMiddleware(MiddlewareMixin):
    """
    Authentication middleware that allows users to use HTTP Auth Basic instead
    of requiring the user to be in the session. Allows using of a Knox token in
    place of password.
    """

    def process_request(self, request):
        # Authentication middleware must be active.
        assert hasattr(
            request, 'user'
        ), 'AuthenticationMiddleware must be active'
        # We are already done if the user is already authenticated.
        if request.user.is_authenticated:
            return
        # Allow disabling of basic auth alltogether in configuration.
        if getattr(settings, 'BASICAUTH_DISABLE', False):
            return
        # When user is not logged in, try to login via HTTP_AUTHORIZATION
        # header. If this header is not set, send the response to ask for
        # Auth Basic.
        if 'HTTP_AUTHORIZATION' not in request.META:
            return
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2 and auth[0].lower() == 'basic':
            uname, passwd = base64.b64decode(auth[1]).decode().split(':')
            user = authenticate(username=uname, password=passwd)
            if user:
                login(request, user)
                return
            # If not authenticated, try token
            token_auth = TokenAuthentication()
            try:
                user, _ = token_auth.authenticate_credentials(
                    passwd.encode('utf-8')
                )
            except Exception:
                return
            if user and user.is_authenticated and user.username == uname:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                return

    def process_response(self, request, response):
        if not request.user.is_authenticated:
            realm = getattr(settings, 'BASICAUTH_REALM', 'Protected Realm')
            response = HttpResponse()
            response.status_code = 401
            response['WWW-Authenticate'] = 'Basic realm="%s"' % realm
        return response


def cbv_decorator_from_middleware(middleware):
    """A variant for decorator_from_middleware for class-based views."""

    def decorator(cls):
        dispatch = cls.dispatch

        @wraps(dispatch)
        @method_decorator(decorator_from_middleware(middleware))
        def wrapper(self, *args, **kwargs):
            return dispatch(self, *args, **kwargs)

        cls.dispatch = wrapper
        return cls

    return decorator


# Decorator for FallbackToAuthBasicMiddleware
fallback_to_auth_basic = cbv_decorator_from_middleware(
    FallbackToAuthBasicMiddleware
)
