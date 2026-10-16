.. _app_samplesheets_export:

Exporting Sample Sheets
^^^^^^^^^^^^^^^^^^^^^^^

There are two methods of exporting sample sheets in the Sample Sheets app UI:
full export of the investigation as ISA-Tab and individual study or assay table
export as an Excel table. This section details both methods.


Export ISA-Tab
==============

To export the project sample sheets as ISA-Tabs, open the
:guilabel:`Sheet Operations` dropdown and select :guilabel:`Export ISA-Tab`.

This exports the entire investigation with all studies and assays as a zip
archive containing all the ISA-Tab files as tab separated values (TSV). The
export is fully ISA-Tab compatible and can be used with other software
supporting the model.

.. include:: _include/sheets_zip_warning.rst

If you want to omit SODAR specific metadata comments such as project UUIDs from
the exported files, you can select :guilabel:`Export Without SODAR Metadata`.
For more information on this metadata, see
:ref:`metadata_advanced_sodar_export`.

.. hint::

    If you plan to use an exported ISA-Tab in another SODAR project or on
    another SODAR instance, it is strongly recommended to export it *without*
    the SODAR-specific metadata. If present, this information is retained on
    import in :ref:`ISA-Tab versions <app_samplesheets_version>`. Having e.g.
    UUIDs referring to projects other than the current one may create user
    confusion.


Export Excel Table
==================

Individual study or assay tables can be exported as Excel compatible tables from
the Sample Sheets app UI. This is useful if one wants to e.g. easily access
certain columns for operations in spreadsheet software. Exporting a table is
done by clicking the export button on the right hand side of the table header.

.. figure:: _static/app_samplesheets/sheet_export_button.png
    :align: center
    :scale: 75%

    Sample sheet Excel table export button

.. warning::

    The data exported as an Excel table is **not** ISA-Tab compatible and it
    can't be used in place of an ISA-Tab TSV. Furthermore, some data may be
    rendered differently than in the actual ISA-Tab.
