"""Config for drf-spectacular"""


def exclude_knox_hook(endpoints):
    """Exclude django-knox-auth endpoints from spectacular OpenAPI generation"""
    filtered = []
    for path, path_regex, method, callback in endpoints:
        if not path.startswith('/api/auth/log'):
            filtered.append((path, path_regex, method, callback))
    return filtered
