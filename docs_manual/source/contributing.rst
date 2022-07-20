.. _contributing:

Contributing
^^^^^^^^^^^^

Contributions to SODAR are welcome and they are greatly appreciated! Every
little bit helps, and credit will always be given. You can contribute in many
ways detailed in the following subsection.

.. note::

    Please ensure your feedback and contributions are directed at the correct
    repository. The `SODAR <https://github.com/bihealth/sodar-server/>`_
    repository contains the functionalities for sample sheets, landing zones,
    ontology access and iRODS operations. For more details, see :ref:`dev_apps`.

    Other applications, project management functionalities and the general UI
    can be found in `SODAR Core <https://github.com/bihealth/sodar-core/>`_.

.. warning::

    SODAR repositories and their issue trackers are publicly viewable. Please
    ensure you do **not** include any sensitive information such as patient or
    donor IDs (even pseudonymous ones) in your feedback or contributions. This
    includes e.g. issue descriptions, screenshots, logs for bug reports and
    documentation.


Types of Contributions
======================

Report Bugs
-----------

Report bugs through the
`SODAR issue tracker <https://github.com/bihealth/sodar-server/issues>`_
in GitHub.

When reporting a bug, please follow the provided template. Make sure to include
the following information:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.

Make sure your report does not contain any sensitive information regarding e.g.
patients and donors.

Fix Bugs
--------

Look through the issue tracker for bugs. Anything tagged with ``bug`` and
``help wanted`` is open to whoever wants to implement it.

Implement Features
------------------

Look through the issue tracker for features. Anything tagged with ``feature``
and ``help wanted`` is open to whoever wants to implement it.

Write Documentation
-------------------

SODAR can always use more documentation, whether as part of the SODAR Manual, in
docstrings, or even on the web in blog posts, articles, and such.

For contributing to the SODAR Manual official documentation, see
:ref:`Documentation Guidelines <dev_guide_doc>`.

For editing docstrings, see :ref:`dev_guide_code`.

Submit Feedback
---------------

The best way to send feedback is to file an issue in the issue tracker.

If you are proposing a feature:

- Follow the provided template.
- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are
  welcome :)


Get Started
===========

Ready to contribute code to SODAR? Here are the steps to get started.

1. Fork the `sodar-server <https://github.com/bihealth/sodar-server>`_ repo on
   GitHub.

2. Clone your fork locally. ::

    $ git clone git@github.com:your_name_here/sodar-server.git

3. Set up SODAR for development. For instructions see :ref:`dev_install`.

4. Create a branch for local development. Make sure to base it on the ``dev``
   branch. You can now make your changes locally. ::

    $ git checkout -b 123-branch-name dev

5. When you're done making changes, make sure to apply proper formatting using
   Black and the settings specified in the accompanying ``black.sh`` script.
   Next, check that your changes pass flake8. Finally, run the tests. It is
   recommended to use the ``Makefile`` to ensure the correct Django
   configuration for testing is selected. ::

    $ ./black.sh
    $ flake8 .
    $ make test
    $ make test_samplesheets_vue

6. Once the tests and flake8 pass, commit your changes and push your branch to
   GitHub. ::

    $ git add .
    $ git commit -m "add/update/fix issue-description-here (#issue-id)"
    $ git push origin 123-branch-name

7. Submit a pull request through the GitHub website.

For specific requirements and recommendations regarding work branches, commits
and pull requests, see :ref:`dev_guide`.

For guidelines regarding the code itself, see :ref:`dev_guide_code`.
