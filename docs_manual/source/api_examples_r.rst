.. _api_examples_r:

API Examples for R
^^^^^^^^^^^^^^^^^^

This document presents examples of SODAR API use in R. The examples assume you
have access to a running instance of the SODAR server. You also need contributor
access or above to at least one existing category.


Libraries
=========

In R, you can use the ``httr`` library to interact with the SODAR API.  We
also will load the ``jsonlite`` library to handle JSON encoding and decoding.

.. code-block:: r

    library(httr)
    library(jsonlite)

The examples below will show how to directly use the ``httr`` functions to
interact with the SODAR REST API. If you want a more high-level interface, you
can use the `LimsaR R package <https://github.com/bihealth/LimsaR>`_.


Setup
=====

First, we need to set up the connection parameters and headers for
authentication.

.. code-block:: r

    # URL of your SODAR server
    sodar_url <- 'https://YOUR-URL-HERE'

    # API token: create yourself a token in the API Tokens app
    # Your user UUID: see the User Profile app for this value
    user_uuid <- '11111111-1111-1111-1111-111111111111'
    api_token <- 'YOUR-API-TOKEN-HERE'

    # UUID for a category in which you have at least contributor access
    category_uuid <- '22222222-2222-2222-2222-222222222222'

Then, we set up the headers for the requests. Providing accept headers is not
explicitly required, but strongly recommended. Including the accept header helps
ensure you are calling a version of the API which is compatible with your
requests and returns expected results.

.. code-block:: r

    # Token authorization header (required)
    auth_header <- paste0('token ', api_token)

    # Use project_headers for project management API endpoints
    project_headers <- add_headers(
      Authorization = auth_header,
      Accept = 'application/vnd.bihealth.sodar-core.projectroles+json; version=2.0'
    )

    # Use the following headers for sample sheet and landing zone API endpoints
    sheet_headers <- add_headers(
      Authorization = auth_header,
      Accept = 'application/vnd.bihealth.sodar.samplesheets+json; version=1.2'
    )

    zone_headers <- add_headers(
      Authorization = auth_header,
      Accept = 'application/vnd.bihealth.sodar.landingzones+json; version=1.1'
    )


Simple Operations
=================

First, we can check that the connection is working by retrieving details for
the current user. This uses the projectroles API, so we need to use the
respective header. We will issue a GET request to the user retrieve endpoint
using the ``GET`` function from ``httr``.

.. code-block:: r

    url <- paste0(sodar_url, '/project/api/users/current')
    response <- GET(url, project_headers)

The ``response`` object is a list containing the server response, including
the status code and the content. We can parse the content as follows:

.. code-block:: r

    # show the status code – refer to the API documentation for details
    response$status_code

    # parse the server response content
    content <- fromJSON(rawToChar(response$content))
    content

    # we can also get our UUID from the content
    user_uuid <- content$sodar_uuid

This will show the following information about the current user::

    $username
    [1] "doej@DOMAIN"

    $name
    [1] "John Doe"

    $email
    [1] "john.doe@whatever.org"

    $additional_emails
    list()

    $is_superuser
    [1] FALSE

    $auth_type
    [1] "LDAP"

    $sodar_uuid
    [1] "33333333-3333-3333-3333-333333333333"

Another useful operation is to list the projects and categories which are
available to you. This also uses the projectroles API, so we again use the
respective header.

.. code-block:: r

    url <- paste0(sodar_url, '/project/api/list')
    response <- GET(url, project_headers)
    content <- fromJSON(rawToChar(response$content))

The ``fromJSON`` function is smart enough to return a data frame, helpfully
listing projects and categories, one item per row.

In a similar way, you can list all users known to the SODAR server:

.. code-block:: r

    url <- paste0(sodar_url, '/project/api/users/list')
    response <- GET(url, config=conf, project_headers)
    content <- fromJSON(rawToChar(response$content))


Create Project
==============

To create a project, we need at least a title and category UUID where the
project should be created. We can optionally provide additional information
such as description, readme and whether or not public access to the project
should be granted to non-members.

.. code-block:: r

    url <- paste0(sodar_url, '/project/api/create')

    # prepare the project
    project <- list(
      title = 'New Project via API',
      type = 'PROJECT',
      parent = category_uuid,
      public_access = NA,
      owner = user_uuid
    )

    # send the request
    response <- POST(
      url,
      body = project,
      encode = "json",
      project_headers
    )

    content <- fromJSON(rawToChar(response$content))
    project_uuid <- content$sodar_uuid

The ``content`` object now contains information about the newly created
project, including its UUID, which we can use for further operations.

We use the ``public_access = NA`` parameter to indicate that the
project should not be public. If you want to create a public project, set
public access to the desired role. Currently supported roles are
``project guest`` and ``project viewer``.

.. note::

    Data provided to ``POST``, ``PUT`` or ``PATCH`` requests should be JSON
    encoded unless otherwise noted. This is done using the ``encode="json"``
    parameter in the ``httr`` functions ``POST``, ``PUT``, and ``PATCH``.


Assign a Member Role
====================

To grant access to a project or category to another user, you need to
assign them a role using the projectroles API.  Below, we assign the user
whose UUID is stored in the ``other_user_uuid`` variable the role of
``project contributor`` in the newly created project.

If you need to provide access to the project to another user account, see the
following example. A successful request returns details of the role assignment
including its UUID for future updates.

.. code-block:: r

    other_user_uuid <- '33333333-3333-3333-3333-333333333333'
    url <- paste0(sodar_url, '/project/api/roles/create/', project_uuid)

    role <- list(
      role = 'project contributor',
      user = other_user_uuid
    )

    response <- POST(
      url,
      body = role,
      encode = "json",
      project_headers
    )

    content <- fromJSON(rawToChar(response$content))

    role_uuid <- content$sodar_uuid

The ``role_uuid`` variable now contains the UUID of the newly created role
and you can use it for future updates or deletions.

Import Sample Sheet
===================

To import ISA-Tab sample sheets into the project, you can either upload the
necessary files (investigation, study, and assay TSV files) or a ZIP archive
containing all these files. We start with the former; please note that we
now start using the samplesheets API defined in the SODAR server package.
In the following example, I assume that the zip archive is named
``isatab.zip`` and is located in the current working directory.

.. code-block:: r

    url <- paste0(sodar_url, '/samplesheets/api/import/', project_uuid),
    body <- list(file = upload_file("isatab.zip"))

    response <- POST(
      url,
      body = body,
      encode = "multipart",
      sheet_headers
    )

If you prefer to upload multiple ISA-Tab files instead of a Zip archive, you can
do so as follows. We can simply upload all files from a single directory,
e.g. ``isatab/``. Note that the names of the files in the ``files`` list are
arbitrary.

.. code-block:: r

    files <- list.files("isatab", full.names = TRUE)
    names(files) <- basename(files)
    body <- lapply(files, upload_file)

    # the rest is the same as above
    response <- POST(
      url,
      body = body,
      encode = "multipart",
      sheet_headers
    )

.. note::

    Importing partial investigations is not allowed. When importing data as
    multiple ISA-Tab TSV files, all study and assay files of the investigation
    must be present or your import will fail.

To ensure your import was successful, you can retrieve investigation information
via the API. This also returns e.g. the UUIDs for studies and assays:

.. code-block:: r

    url <- paste0(sodar_url, '/samplesheets/api/investigation/retrieve/', project_uuid)
    response <- GET(url, sheet_headers)
    inv_info <- fromJSON(rawToChar(response$content))


Export Sample Sheets
====================

There are several ways to export sample sheets from SODAR. In this example, we
export them as ISA-Tab TSV data wrapped in a JSON structure. This allows you to
easily parse the data and convert it into data frames for further processing.

.. code-block:: r

    url <- paste0(sodar_url, '/samplesheets/api/export/json/', project_uuid)
    response <- GET(url, sheet_headers)
    content <- fromJSON(rawToChar(response$content))

    # convert first assay table to data frame
    assay_df <- read.delim(text = content$assays[[1]]$tsv, sep = "\t", header = TRUE)


Landing Zones Management
========================

Before you can create landing zones and upload files, you need first to create
an iRODS collection for your sample data. From the API you can do this as
follows, again using the samplesheets API.

.. code-block:: r

    url <- paste0(sodar_url, '/samplesheets/api/irods/collections/create/', project_uuid)
    response <- POST(url, sheet_headers)

The API request below initiates the asynchronous process for creating a landing
zone. As each zone must be associated with an assay, you need to provide an
assay UUID, which you can retrieve from the investigation information API
endpoint as detailed above. Note that we are now using the landingzones API
from the SODAR server package, so we use the respective headers.

.. code-block:: r

    assay_uuid <- inv_info$studies[[1]]$assays[[1]]$sodar_uuid
    url <- paste0(sodar_url, '/landingzones/api/create/', project_uuid)
    response <- POST(
      url,
      body = list(assay = assay_uuid),
      encode = "json",
      zone_headers
    )

    content <- fromJSON(rawToChar(response$content))
    zone_uuid <- content$sodar_uuid

As with most landing zone operations, the landing zone creation process is
asynchronous. You need to ensure the zone status has been changed to ``ACTIVE``
before proceeding with file uploads:

.. code-block:: r

    url <- paste0(sodar_url, '/landingzones/api/retrieve/', zone_uuid)
    response <- GET(url, zone_headers)
    fromJSON(rawToChar(response$content))$status

In scripts you will want to make sure that the LZ becomes active before
continuing. You can do this by polling the status until it becomes ``ACTIVE``,
for example as follows:

.. code-block:: r

    lz_status <- function(zone_uuid) {
      url <- paste0(sodar_url, '/landingzones/api/retrieve/', zone_uuid)
      response <- GET(url, zone_headers)
      fromJSON(rawToChar(response$content))$status
    }

    while((lzs <- lz_status(zone_uuid)) != "ACTIVE") {
      message("LZ status is ", lzs, ", waiting...")
      Sys.sleep(1)
    }

Once the LZ becomes active, you can upload files using iRODS iCommands or file
uploading scripts – this operation is not done using the SODAR API. After
uploading, you can trigger the asynchronous validation and moving process as
follows:

.. code-block:: r

    url <- paste0(sodar_url, '/landingzones/api/submit/move/', zone_uuid)
    response <- POST(url, zone_headers)

Once the landing zone status is returned as ``MOVED``, the landing zone files
have been moved into the project sample data repository and the zone has been
deleted.
