.. _metadata_recording:

Metadata Recording
^^^^^^^^^^^^^^^^^^

The :ref:`sample sheet editor <app_samplesheets_edit>` in SODAR is under
construction and does not yet support the full set of features for creating and
editing sample sheets. Until these features are finished, CUBI will prepare the
necessary tabular files (ISA-Tab) corresponding to your project and provide them
to you to fill out in Excel or your spreadsheet application of choice.

The process currently includes the following steps:

1. **Preparation** - Tell us about the project and we set up appropriate
   ISA-Tab files from our templates.
2. **Recording** - Fill out the study and assay sheets with your metadata.
3. **Validation** - Send us the files for some pre-processing and validation.
4. **Upload** - Upload the ISA-Tab files to the corresponding SODAR project.

SODAR utilizes the `ISA framework`_ and in particular the ISA-Tab format to
integrate experimental metadata into SODAR projects. To facilitate the
recording of metadata in consistent and valid ISA-Tab files (as far as
possible), this document provides a brief introduction on the ISA-Tab format
and defines rules to consider when editing them in Excel and co.

.. _ISA framework: https://isa-tools.org/


Background
==========

About ISA-Tab
-------------

ISA (short for **I**\nvestigation, **S**\tudy and **A**\ssay) is an open
source framework for standardizing metadata for scientific experiments.

An ISA **investigation** can consist of several **studies** and each **study**
can contain several **assays** (experiments of one measurement type and
method, e.g. transcriptome profiling using nucleotide sequencing aka RNA-Seq
or protein expression profiling using mass spectrometry).

In practice, projects in SODAR will mostly consist of one study including one
assay (or sometimes more, e.g. for multi-omics studies). In this common case,
an ISA-Tab project will consist of three files:

1. **Investigation** file (``i_Investigation.txt``), containing general project
   information including i.a. study and assay titles, descriptions and
   relations.
2. **Study** file (``s_STUDY-ID.txt``), a tabular file describing samples and
   corresponding sources.
3. **Assay** file (``a_STUDY-ID_ASSAY-TYPE.txt``), a tabular file describing
   sample processing and measurement as well as corresponding data files.

In the case of several studies or assays, each study and assay is
represented by one distinct tabular file.

Tabular File Structure
----------------------

In a study or assay file, each row represents an ordered chain of
materials/data and transforming processes to illustrate the procedure of the
experiment, from sample collection over preparation and measurement to data
generation and processing.

Materials/data and processes are represented by cohesive blocks of several
columns/fields. **Material**/**data** blocks start with an identifier column
(*Source Name*, *Sample Name*, *Extract Name*, *Labeled Extract Name* or
*\* File* in the case of data), followed by descriptive columns
(*Characteristics[\*]*, each potentially followed by a *Unit* column if
appropriate). **Process** blocks start with a *Protocol REF* column which
references a predefined protocol by name (which are declared
in the investigation file), followed by descriptive columns (*Parameter
Value[\*]*). Both types of blocks can contain *Comment[\*]* columns.

*Characteristics[\*]*, *Unit* and *Parameter Value[\*]* columns might be
followed by *Term Source REF* and *Term Accession Number* columns, indicating
the potential use of linked ontology terms for this characteristic, unit or
parameter, resp.

ISA-Tab makes use of several predefined and expected materials (*Source Name*,
*Sample Name*, *Extract Name*, *Labeled Extract Name*). Furthermore, some
columns are unique and exceptional in terms of not being standard
descriptive columns (such as *Characteristics[\*]*, *Parameter Value[\*]*,
etc.), but still being associated with a specific material or process. These
include, for instance, *Label* (for material *Labeled Extract Name*),
*Performer* and *Date* (for all processes), *Assay Name* (for processes with
Protocol REF "Nucleic acid sequencing") or *MS Assay Name* (for processes
with Protocol REF "Mass spectrometry").

A very simple study tabular file may look like this:

.. list-table:: Study tabular file example
   :header-rows: 1

   * - Source Name
     - Characteristics [Organism]
     - Protocol REF
     - Performer
     - Date
     - Sample Name
   * - PatientX
     - Homo sapiens
     - Sample Collection
     - John Doe
     - 11.11.2011
     - BloodSample1

While a study file ends with a Sample material block (starting with the *Sample
Name* column), corresponding assays reference these samples by identifier in the
first column (also called *Sample Name*, characteristics and co are not
repeated, though).

A very simple assay tabular file may look like this:

.. list-table:: Assay tabular file example
   :header-rows: 1

   * - Sample Name
     - Protocol REF
     - Protocol REF
     - Parameter Value [Instrument]
     - Parameter Value [Mass analyzer]
     - Raw Spectral Data File
   * - BloodSample1
     - Chromatography
     - Mass spectrometry
     - Thermo Scientific™ Q Exactive
     - orbitrap
     - 20111125_PX_BS1.raw

In practice, study and assay files will feature much more columns.

Splitting and Pooling
---------------------

The concept of splitting and pooling can be used in the study and assay tabular
files to represent, e.g. the collection of different samples from the same
source (splitting), the creation of technical replicates (splitting) or
collective multiplexed/multi-label measurements such as with SILAC and co
(pooling).

Splitting is represented by repeating the identifier (and corresponding
characteristics etc.) of the materials of origin. E.g. representing several
samples of the same source looks as follows (simplified ISA-Tab study table
excerpt without any characteristics, parameters, etc.):

.. list-table:: Splitting example
   :header-rows: 1

   * - Source Name
     - Protocol REF
     - Sample Name
   * - PatientX
     - Sample collection
     - Tissue1
   * - PatientX
     - Sample collection
     - Tissue2

Similar, materials can be pooled to depict collective processing by repeating
the target materials or process names (simplified ISA-Tab assay table excerpt
without any characteristics, parameters, etc.):

.. list-table:: Pooling example
   :header-rows: 1

   * - Extract Name
     - Protocol REF
     - Labeled Extract Name
     - Label
     - Protocol REF
     - MS Assay Name
   * - Extract1
     - Labeling
     - LabeledExtract1
     - Light
     - Mass spectrometry
     - Run1
   * - Extract2
     - Labeling
     - LabeledExtract2
     - Heavy
     - Mass spectrometry
     - Run1

For more details on the ISA model and the ISA-Tab format, please have a look at
the `ISA documentation`_.

.. _ISA documentation: https://isa-specs.readthedocs.io/en/latest/


1. Preparation
==============

Some basic information about the project is needed to initiate the SODAR
project and the ISA-Tab files.

For the SODAR **project**, please provide a **project title** and a **short
description** as well as the **people** who should be associated with the
project. In general, all people with valid Charite or MDC account are
eligible to access SODAR and thus can be associated with a project.
Following roles are available:

* **Project owner**: usually the PI in charge of and accountable for the
  project and (meta-) data.
* **Project delegate**: second in charge, maybe a PI of a collaborating lab
  (optional).
* **Project contributor(s)**: staff who is generating and uploading (meta-)
  data (optional but recommended).
* **Project guest(s)**: people who are supposed to view but not alter any
  (meta-) data (optional).

Furthermore, indicate the **studies** and **assays** needed.

SODAR project information are recycled in the corresponding ISA-Tab. Depending
on the extend of the project, the SODAR title and description may be applied
either to the ISA investigation or to an ISA study. If the project (and thus
investigation) is supposed to contain several studies, each **study** needs an
own **title**, **short description** as well as **short identifier**. In the
case of one-study projects, no specific investigation information is
required and the project title and description may be reflected as the title
and description of the single study. Only an additional study identifier is
needed then.

In most cases one study might be sufficient. Several studies can be used for
instance to keep a clean separation between different cohorts in a project.
Other classifications of data/studies might be more appropriate using the
multi-level categorization of projects in SODAR, e.g. the association of
different projects with a collaboration partner or customer.

Each study may comprise several assays, though. Therefore indicate the type(s)
of data measured and the technology used. Currently, CUBI provides assay
templates for the following measurement types and technologies/methods:

.. list-table:: Available assay templates
   :header-rows: 1

   * - Measurement
     - Technology/method
   * - genome sequencing
     - nucleotide sequencing
   * - exome sequencing
     - nucleotide sequencing
   * - transcription profiling
     - nucleotide sequencing
   * - metabolite profiling
     - mass spectrometry
   * - protein expression profiling
     - mass spectrometry
   * - protein identification
     - mass spectrometry

After sending us these information, we will initiate the SODAR project (you
might do so on your own, if you are owner of a category in SODAR) and prepare
and provide the corresponding ISA-Tab files to fill out.


2. Recording
============

Use a familiar spreadsheet program such as MS Office Excel or LibreOffice Calc
to add and edit metadata in the study and assay tab files. If the file format
is not recognized right away, the spreadsheet program may ask for the format
specifics. In this case the following settings should be applied:

* MS Office Excel (english)
    * Original data type: Delimited
    * File origin: 65001 : Unicode (UTF-8)
    * Delimiters: Tabstopp
    * Text qualifier: "
* MS Office Excel (german)
    * Ursprünglicher Datentyp: Getrennt
    * Dateiursprung: 65001 : Unicode (UTF-8)
    * Trennzeichen: Tabstopp
    * Textqualifizierer: "
* LibreOffice Calc (english)
    * Character Set: Unicode (UTF-8)
    * Separate options: Separate by - Tab
    * String delimiter: "
* LibreOffice Calc (german)
    * Zeichensatz: Unicode (UTF-8)
    * Trennoptionen: Getrennt - Tabulator
    * Zeichenketten-Trennzeichen: "

Once the file is open, it should feature a header row in the structure as
described above based on the template selected for the project. It is now ready
for recording or editing metadata. Processes (i.e. *Protocol REF* columns) are
already linked to the corresponding protocol by name reference for a default of
50 rows which should be reduced or extended, depending on the rows needed.
Remember, materials and processes may repeat over several rows, if they are
part of a splitting or pooling procedure. Furthermore, consider the following
restrictions.

Editing Restrictions
--------------------

ISA-Tab is a strictly defined/specified format and is prone to errors when
things change uncontrollably, for instance with respect to indentation,
encoding (UTF-8) and also content (available columns, declared protocols,
parameters, etc.). Thus, the following notes are intended as rules or
restrictions to keep the ISA-Tab files as consistent and valid as possible when
the data is filled in manually, i.e. via Excel and co.

Please consider following the described rules/restrictions as much as possible,
as it will benefit quick validation/postprocessing and upload to SODAR.
Otherwise indicate necessary changes when sending us the files.

Explaining the technical reasons of these rules/restrictions is out of scope of
this document.

* **Investigation file**
    * Editing the investigation file manually is not recommended.
    * In particular, never open and save the investigation file
      (i_investigation.txt) with Excel, LibreOffice Calc or similar. It will
      mess up indentation and thereby render the file unusable.

* **Study and assay files**
    * Always save the file in the same format as it was opened: tab-separated
      text file (txt).

* **Adding and deleting columns**
    * **Don't delete any columns!** Leave fields empty which are not of
      interest for your project.
    * Adding *Comment[\*]* columns to any material/data or process block
      shouldn't result in any problems.
    * Adding *Characteristic[\*]* columns to any material block shouldn't
      result in any problems.
    * Please refrain from manually adding *Parameter Value[\*]* columns in
      process blocks.
    * Please refrain from adding any other type of column. However, feel free
      to discuss/request additional columns upfront, in particular if they
      might be reasonable general addition to the templates.

* **Pooling and splitting**
    * Make sure repeated materials/processes include not only the same
      identifier but also the same metadata, i.e. same values in
      *Characteristic[\*]*, *Parameter Value[\*]* and *Comment[\*]* columns,
      etc.

* **Processes**
    * When adding more rows, fill up *Protocol REF* columns with previous
      values.
    * Don't remove values in *Protocol REF* fields of used rows.
    * Remove values in *Protocol REF* fields of unused rows.

* **Ontology**
    * Don't manually fill out the ontology columns *Term Source REF* and
      *Term Accession Number*.
    * Values in potential ontology columns will be checked and linked in our
      postprocessing, if applicable.

* **Special characters**
    * If the encoding of the file is corrupted, special characters (e.g. as in
      "μmol") might be faulty as well.
    * As this is difficult to assess/avoid manually, please just indicate any
      use of special characters when sending the file to us for validation.

We will extend this list with more rules/restrictions as soon as more pitfalls
show up.


3. Validation (Post-Processing)
===============================

Under good circumstances, a direct upload to the corresponding SODAR project
may be successful already. Feel free to give it try (see
:ref:`metadata_recording_4_uploading`). Otherwise, the upload may fail due
to invalid ISA-Tab files based on various reasons. Thus, you can send the
data to us for validation, corrections (if necessary) and optional
post-processing.

Post-processing may include i.a. the association of potential ontology terms
with appropriate ontology identifier and sources.


.. _metadata_recording_4_uploading:


4. Uploading
============

Uploading metadata into a SODAR project can be facilitated by CUBI (e.g. after
validation) or any project member with appropriate role (owner, delegate, or
contributor).

To upload sample sheets into SODAR, first navigate into the **Sample Sheets**
application within the corresponding project. In the
:guilabel:`Sheet Operations` dropdown, select :guilabel:`Import ISA-Tab`. If you
are replacing existing sheets in the project, this option will appear as
:guilabel:`Replace ISA-Tab`.

In the import form, the ISA-Tab TSV files can either be imported as separate
files, or a Zip archive containing all of the files in the same directory.

.. include:: _include/sheets_zip_warning.rst

After uploading, it is recommended to compare and validate the number of
study and assay rows between the SODAR project and ISA-Tab files to exclude
mistakes in metadata recording, in particular with respect to splitting and
pooling.
