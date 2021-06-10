.. _metadata_advanced:

Advanced Metadata Topics
^^^^^^^^^^^^^^^^^^^^^^^^

Advanced metadata topics are detailed in this document. These are intended for
e.g. advanced users who manually prepare their own sample sheets for specific
study types.


Study iRODS Data Linking
========================

The sample sheet view of the SODAR UI display shortcuts to relevant iRODS files
and `IGV <https://software.broadinstitute.org/software/igv/>`_ integration.
These are displayed on the right hand side column of the *study table*. The
types of shortcuts displayed depend on the **study plugin**.

The study plugin selected by SODAR in turn depends on the
**study configuration**. The configuration usually originates from the template
used to create the sample sheet. SODAR reads this configuration from the
investigation TSV file in a comment labeled ``Created with Configuration``.

SODAR currently supports the following study configurations:

- **Cancer**
    * Indended for: Cancer studies
    * Configuration: ``bih_cancer``
    * Provides: **sample specific** shortcuts to the latest BAM and VCF files.
- **Germline**
    * Indended for: Germline studies
    * Configuration: ``bih_germline``
    * Provides: **pedigree specific** shortcuts to the latest BAM and VCF files.

If the configuration is not specified or is not known to SODAR, the shortcut
column will not be visible.


Assay iRODS Data Linking
========================

Similar to study data linking, SODAR also displays iRODS links specific to
assays according to an **assay plugin**. The selected plugin affects the
following types of iRODS links:

- **Assay shortcuts** card above each assay table
- **Row-specific links** in the right hand column of each row
- **Inline links** which are file names stored in the table itself, under e.g.
  "data file" materials.

The assay plugin to be used is determined based on a combination of the
*measurement type* and *technology type* attributes of each assay.

If SODAR doesn't recognize the measurement type and technology combination, no
plugin will be applied. In this case the row-specific links will point to the
root collection of the assay.

SODAR currently supports the following assay plugins:

- **DNA Sequencing**
- **Metabolite Profiling / Mass Spectrometry**
- **Microarray**
- **Protein Expression Profiling / Mass Spectrometry**

Common links as well as plugin specific links are detailed below.

Common Links
------------

Links to the following iRODS collections are provided for *all* assay
configurations in the assay shortcuts card:

- ``ResultsReports``: Collection for assay specific result and report files
- ``MiscFiles``: Miscellaneous files
- ``TrackHubs``: Track hubs for UCSC Genome Browser integration (displayed if
  track hubs have been created)

DNA Sequencing Plugin
---------------------

- Additional assay shortcuts
    * N/A
- Row-specific links
    * Each row links to the **last material name** in the row, not counting
      "data file" materials.
- Inline links
    * N/A
- Used with measurement type / technology type
    * genome sequencing / nucleotide sequencing
    * exome sequencing / nucleotide sequencing
    * transcription profiling / nucleotide sequencing
    * panel sequencing / nucleotide sequencing

Metabolite Profiling / Mass Spectrometry Plugin
-----------------------------------------------

- Additional assay shortcuts
    * ``RawData``: Assay-wide raw data files
- Row-specific links
    * N/A
- Inline links
    * *Metabolite assignment files* are linked to ``MiscFiles``
    * *Raw spectral data files* are linked to ``RawData``
    * *Report files* are linked to ``ResultsReports``
- Used with measurement type / technology type
    * metabolite profiling / mass spectrometry

Microarray Plugin
-----------------

- Additional assay shortcuts
    * N/A
- Row-specific links
    * Rows with *hybridization assay name* and *scan name* are linked under
      ``RawData/{hybrid name}/{scan name}/``.
- Inline links
    * Inline file names are linked to row-specific hybridization assay name and
      scan name paths.
- Used with measurement type / technology type
    * transcription profiling / microarray
    * transcription profiling / DNA microarray

Protein Expression Profiling / Mass Spectrometry Plugin
-------------------------------------------------------

- Additional assay shortcuts
    * ``RawData``: Assay-wide raw data files
    * ``MaxQuantResults``: Assay-wide MaxQuant result files
- Row-specific links
    * N/A
- Inline links
    * Files are linked to `RawData` under the assay.
- Used with measurement type / technology type
    * protein expression profiling / mass spectrometry
