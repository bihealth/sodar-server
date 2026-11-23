from setuptools_scm import get_version

__version__ = get_version(
    version_scheme='no-guess-dev',
    local_scheme='no-local-version',
    search_parent_directories=True,
)
