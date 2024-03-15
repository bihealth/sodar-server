.. _api_examples:

API Examples
^^^^^^^^^^^^

In this document we present examples of using SODAR via the REST API. It is
possible to adapt these examples to automate activity via scripts, command line
tools, notebooks or other external software. In these examples, we call the API
using the Python ``requests`` package.

.. code-block:: python

    import requests

The rest of these examples assume you have access to an existing SODAR server.
You also need contributor access or above to at least one existing category.

The examples show basic functionality with default options unless otherwise
stated. For all parameters and options for requests, see the detailed API
documentation of the relevant API endpoints.


Setup
=====

To get started, you need to retrieve and set up certain variables for accssing
the SODAR API:

.. code-block:: python

    # URL of your SODAR server
    sodar_url = 'https://YOUR-URL-HERE'
    # API token: create yourself a token in the API Tokens app
    # Your user UUID: see the User Profile app for this value
    user_uuid = '11111111-1111-1111-1111-111111111111'
    api_token = 'YOUR-API-TOKEN-HERE'
    # UUID for a category in which you have at least contributor access
    category_uuid = '22222222-2222-2222-2222-222222222222'

    # Headers for requests:
    # Token authorization header (required)
    auth_header = {'Authorization': 'token {}'.format(api_token)}
    # Use core_headers for project management API endpoints
    core_headers = {**auth_header, 'Accept': 'application/vnd.bihealth.sodar-core+json; version=0.13.4'}
    # Use sodar_headers for sample sheet and landing zone API endpoints
    sodar_headers = {**auth_header, 'Accept': 'application/vnd.bihealth.sodar+json; version=0.14.2'}

.. note::

    Providing accept headers is not explicitly required, but strongly
    recommended. Including the accept header helps ensure you are calling a
    version of the API which is compatible with your requests and returns
    expected results.

To ensure you can properly connect to SODAR, you can retrieve a list of
categories and projects available to you with the following request:

.. code-block:: python

    url = sodar_url + '/project/api/list'
    projects = requests.get(url, headers=core_headers).json()


Create Project
==============

To create a project, issue a request as displayed in the following example.
Response data for the request will contain the project UUID, which will be
required for most subsequent operations you wish to perform on that project.

.. code-block:: python

    url = sodar_url + '/project/api/create'
    data = {'title': 'New Project via API', 'type': 'PROJECT', 'parent': category_uuid, 'owner': user_uuid}
    project = requests.post(url, data=data, headers=core_headers).json()
    project_uuid = project['sodar_uuid']

.. note::

    Note the use of ``core_headers`` here, as the project management API comes
    from the `SODAR Core <https://sodar-core.readthedocs.io>`_ package, which
    has its own API and versioning.


Assign a Member Role
====================

If you need to provide access to the project to another user account, see the
following example. A successful request returns details of the role assignment
including its UUID for future updates.

.. code-block:: python

    other_user_uuid = '33333333-3333-3333-3333-333333333333'
    url = sodar_url + '/project/api/roles/create/' + project_uuid
    data = {'role': 'project contributor', 'user': other_user_uuid}
    response_data = requests.post(url, data=data, headers=core_headers).json()
    role_uuid = response_data.get('role_uuid')


Import Sample Sheet
===================

The following example demonstrates how you can programmatically import an
existing ISA-Tab into your project. The import API endpoint accepts both ZIP
archives and individual files. In this example, we will be providing a ZIP
archived ISA-Tab.

.. code-block:: python

    url = sodar_url + '/samplesheets/api/import/' + project_uuid
    sheet_path = '/tmp/your_isa_tab.zip'
    files = {'file': ('your_isa_tab.zip', open(sheet_path, 'rb'), 'application/zip')}
    response = requests.post(url, files=files, headers=sodar_headers)

To ensure your import was successful, you can retrieve investigation information
via the API. This also returns e.g. the UUIDs for studies and assays:

.. code-block:: python

    url = sodar_url + '/samplesheets/api/investigation/retrieve/' + project_uuid
    inv_info = requests.get(url, headers=sodar_headers).json()


Export Sample Sheets
====================

There are several ways to export sample sheets from SODAR. In this example, we
export them as ISA-Tab TSV data wrapped in a JSON structure. This enables
providing the TSV data to e.g. parsers for further editing.

.. code-block:: python

    url = sodar_url + '/samplesheets/api/export/json/' + project_uuid
    response_data = requests.get(url, headers=sodar_headers).json()
    print(response_data.keys())
    # dict_keys(['investigation', 'studies', 'assays', 'date_modified'])


Edit and Replace Sample Sheets
==============================

At the moment, editing sample sheets via the REST API is done as follows:

1. Export the ISA-Tab as JSON-wrapped TSV or Zip archive (see "Export Sample
   Sheets").
2. Edit the ISA-Tab TSV data with the tool of your choosing
3. Replace ISA-Tab in iRODS by re-importing the TSV files into your project (see
   "Import Sample Sheets").

If working on Python, we recommend using the
`AltamISA <https://github.com/bihealth/altamisa>`_ parser for editing and
validating your ISA-Tab. Using AltamISA is beyond the scope of this manual. It
is recommended to read further in the
`AltamISA documentation <https://altamisa.readthedocs.org>`_ and go through the
`example of ISA-Tab processing <https://github.com/bihealth/altamisa/blob/master/docs/examples/process_isa_model.py>`_
included in its source code.


Upload Files via Landing Zones
==============================

To enable file uploads, you first have to create sample data repositories for
your sample sheets in iRODS. This can be done as follows. The response returns
the path to the sample repository collection in your project.

.. code-block:: python

    url = sodar_url + '/samplesheets/api/irods/collections/create/' + project_uuid
    response = requests.post(url, headers=sodar_headers)
    irods_path = response.json().get('path')

The API request below initiates the process for creating a landing zone. You
will need to provide an assay UUID, which you can retrieve from the
investigation information API endpoint as detailed above.

.. code-block:: python

    url = sodar_url + '/landingzones/api/create/' + project_uuid
    data = {'assay': assay_uuid}
    response = requests.post(url, data=data, headers=sodar_headers)
    zone_uuid = response.json().get('sodar_uuid')

As with most landing zone operations, the landing zone creation process is
asynchronous. You need to ensure the zone status has been changed to ``ACTIVE``
before proceeding with file uploads:

.. code-block:: python

    url = sodar_url + '/landingzones/api/retrieve/' + zone_uuid
    response_data = requests.get(url, headers=sodar_headers).json()
    if response_data.get('status') == 'ACTIVE':
        pass  # OK to proceed

At this point you can upload files using iRODS iCommands or file uploading
scripts. After uploading, you can trigger the asynchronous validation and
moving process as follows:

.. code-block:: python

    url = sodar_url + '/landingzones/api/submit/move/' + zone_uuid
    response = requests.post(url, headers=sodar_headers)

Once the landing zone status is returned as ``MOVED``, the landing zone files
have been moved into the project sample data repository and the zone has been
deleted.

.. code-block:: python

    url = sodar_url + '/landingzones/api/retrieve/' + zone_uuid
    response_data = requests.get(url, headers=sodar_headers).json()
    if response_data.get('status') == 'MOVED':
        pass  # Moving was successful
