.. _dev_issues:

Issue Tracking and Pull Requests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section guides you through guidelines for SODAR issue tracking, work
branches, commits and pull requests.


Issue Tracking
==============

.. note::

    This section will be updated once the SODAR issue tracker is migrated from
    a private GitLab repo into the public GitHub one.


Work Branches
=============

Base your work branch on the ``dev`` branch. This branch is used for development
and is always the latest "bleeding edge" version of the SODAR server. The
``main`` branch is only used for stable releases.

It is recommended to keep your work branch names short but consistent,
preceeded by the type of change. E.g. ``feature/your-new-feature`` or
``fix/bug-being-fixed``. Appending the name with the related issue ID is also
recommended.


Commits
=======

It is recommended to use short but descriptive commit messages and always
include the related issue ID(s) in the message. Examples:

- ``add local irods auth api view (#1263)``
- ``fix ontology column config tooltip hiding (#1379)``


Pull Requests
=============

Please add the related issue ID(s) to the title of your pull request and ensure
the pull request is set against the ``dev`` branch.

Before submitting a pull request for review, ensure the following:

- All tests pass for ``make test`` and ``make test_samplesheets_vue``.
- ``make black`` has been run for the latest commit.
- ``flake8 .`` produces no errors.
