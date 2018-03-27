"""Utility functions for the filesfolders app"""

from django.urls import reverse


def build_public_url(file, request):
    """
    Return public URL for a file.
    :param file: File object for which public URL will be created
    :param request: HTTP request of View calling the function
    :return: URL (string)
    """
    return request.build_absolute_uri(reverse(
        'filesfolders:file_serve_public',
        kwargs={'secret': file.secret, 'file_name': file.name}))
