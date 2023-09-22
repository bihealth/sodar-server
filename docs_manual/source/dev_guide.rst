.. _dev_guide:

SODAR Development Guidelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This subsection lists specific conventions and guidelines for contributing
code or documentation to SODAR.


Work Branches
=============

Make sure to base your work branch on the ``dev`` branch. This branch is used
for development and is always the latest "bleeding edge" version of SODAR. The
``main`` branch is only used for merging stable releases.

When naming your work branches, prefix them with the issue ID, preferably
followed by a verb depicting the action: "add", "update", "fix", "remove",
"refactor", "upgrade", "deprecate" or something else if none of these ar
applicable.

The rest of the branch name should *concisely* represent the change. It is not
necessary (and often not recommended) to include the entire name of the issue
as they may be verbose.

If a branch and pull request tackles multiple issues at once, including the ID
of the most major issue is enough.

Examples of recommended branch names:

- ``123-add-zone-polarity-reversing``
- ``456-fix-contact-cell-rendering``
- ``789-refactor-irodsbackend-tests``

Commits
=======

It is recommended to use short but descriptive commit messages and always
include the related issue ID(s) in the message. Starting them with the verb
depicting the action is desirable. Examples:

- ``add local irods auth api view (#1263)``
- ``fix ontology column config tooltip hiding (#1379)``


Pull Requests
=============

Please add the related issue ID(s) to the title of your pull request and ensure
the pull request is set against the ``dev`` branch.

It is strongly recommended to use descriptive commit messages even in work
commits that are to be squashed in merging. This will aid the review process.

Before submitting a pull request for review, ensure the following:

- You have followed code conventions (see :ref:`dev_guide_code`).
- You have updated existing tests and/or written new tests as applicable (see
  :ref:`dev_guide_test`).
- You have updated documentation if your pull requests adds or modifies features
  (see :ref:`dev_guide_doc`).
- ``make black`` has been run for the latest commit.
- ``flake8 .`` produces no errors.
- All tests pass with ``make test`` and ``make test_samplesheets_vue``.

Your pull request should work on the Python versions currently supported by the
SODAR dev version. These will be checked by GitHub Actions CI upon pushing your
commit(s).


.. _dev_guide_code:

Code Conventions
================

For developing code for the Django site, see
`SODAR Core code conventions <https://sodar-core.readthedocs.io/en/dev/dev_core_guide.html#code-conventions>`_.

For the samplesheets Vue app, the strict linting used in the development
environment enforces most critical conventions.

.. _dev_guide_test:

Testing Conventions
===================

For testing the Django site, see
`SODAR Core testing conventions <https://sodar-core.readthedocs.io/en/dev/dev_core_guide.html#testing-conventions>`_.

For testing the samplesheets Vue app, unit tests using Jest are expected. Data
from SODAR Ajax API views needs to be mocked. For general hints see
:ref:`dev_resource_vue_test`.


.. _dev_guide_doc:

Documentation
=============

Documentation of SODAR is in the ReStructuredText (RST) format. It is compiled
using Sphinx with the Readthedocs theme. Please follow formatting conventions
displayed in existing documentation. A full style guide will be provided later.

Static assets should be placed under
``docs_manual/source/_static/document_name/``.

Once you have finished your edits, build the documentation to ensure no warnings
or errors are raised. You will need to be in your virtual environment with
Sphinx and other requirements installed.

.. code-block:: bash

    $ cd docs
    $ rm -rf build && make html

It is recommended to **not** update the ``CHANGELOG`` file in pull requests.
This will be done by the maintainers when preparing a release in order to avoid
unnecessary merge/rebase conflicts.
