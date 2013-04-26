oxfama.transmogrifier
=====================

Tranmogrifier pipelines for the analysis and export of Plone content from the
Oxfam America website.

Based on `collective.transmogrifier
<https://pypi.python.org/pypi/collective.transmogrifier>`_ and related tools.

What do You Get?
----------------

This package provides a *transmogrifier* export pipeline which will dump the
field values of the schema of all of the items in the oxfam america website
into a set of CSV files, organized by object type. Each type of object which
has a schema will have its own csv file. Each file will have a header row
which lists the fields output in alphabetical order. Each row after the header
will contain the values for the given fields, if any, present on a single
object within the site. In addition to schema fields, the *path* to the object
within the plone site and the UID and UUID (if present) will be provided.

For file fields (images, files, etc), the value will be a simple string
indicating that the field is a binary file field. No file data will be dumped.

For reference fields, the type and UID of the referenced object(s) will be
listed. This information can be used to look up the referenced object. Simply
find the row with the given UID value in the csv file named for the type.

You can control which fields are output (see *Controlling the Pipeline*
below).

Installing This Package
-----------------------

As this package is unreleased, installing it requires the `mr.developer
<https://pypi.python.org/pypi/mr.developer>`_ buildout extension.

First, include the package in the ``[sources]`` section of your buildout. The
source is in a private repository, so unless you have ssh authentication for
git set up on the machine where you are working, you'll need to use HTTP
authentication:

    oxfama.transmogrifier = git https://github.com/oxfamamerica/oxfama.transmogrifier.git

Next, include the package name in the ``eggs =`` section of the buildout.

    eggs = 
        ...
        oxfama.transmogrifier

Once this is done, you can re-run buildout. You should also see
``collective.transmogrifier`` and ``quintagroup.transmogrifier`` installed as
dependencies of this package.

This package **does not provide** an installable Generic Setup profile, so you
should not expect to see it listed either in the *Add-ons* panel in Plone Site
Setup or in the list of available add-ons when you add a new Plone site.

To verify that the package is properly installed, go to the ZMI (Zope
Management Interface). Find and click on the ``portal_setup`` tool and then
click on the ``import`` tab. Look for the ``Oxfam America Site Dump`` profile
listed in the drop-down list of available Profiles or Snapshots at the top.

Running the Export Pipeline
---------------------------

To run the export dump, you'll need to use the ``portal_setup`` as described
above.  

 * Go to the ZMI
 * Find and click on the ``portal_setup`` tool
 * Click on the ``Import`` tab
 * Find and select the ``Oxfam America Site Dump`` profile in the ``Select
   Profile or Snapshot`` dropdown.
 * Find the ``Run transmogrifier pipeline`` step in the list of available 
   import steps.  Click the checkbox to select it.
 * At the bottom of the page, unselect the ``Include dependencies`` checkbox.
 * Click the ``import selected steps`` button.

The export will run for some time.  You can see progress in the terminal if
you are running the site in ``fg`` mode.  

After all items are dumped, the CSV files will be written to the
``destination`` provided in the pipeline configuration (see *Controlling the
Pipeline* below)

Controlling the Pipeline
------------------------

There are a number of settings you can control for the pipeline. These
controls are available by editing the ``content_to_csv.cfg`` configuration
file in this package. This file is located in
``oxfama/transmogrifier/export``.

The file is organized into a series of sections, each delineated by a
``[name]`` in square brackets.  

The ``[transmogrifier]`` section provides a list of the pipeline sections that
make up the export pipeline as well as the ``local_destination`` which should
be an absolute filesystem path to the folder where the CSV output files will
be written:

    [transmogrifier]
    # configure pipeline and other required information
    pipeline = 
        source
        schemadumper
        writer
        logger

    local_destination = /absolute/path/to/folder

It is vital to ensure that the user running the Plone process have write access
to the destination folder.  If no local destination is provided, the system
will attempt to use ``/tmp``.

The ``[source]`` section provides settings for the ``SiteWalkerSection`` that
is used to walk the object graph of the site and read the contents. You can
provide this section a starting path, if you wish to focus only on one section
of the website. This path should be absolute, based from the ZMI (``/``). The
object identified by the path *will be included*. The walk can be *limited*
using the ``limit`` setting. At most this number of objects will be dumped. If
the setting is omitted, or set to 0, all objects will be dumped:

    [source]
    blueprint = oxfama.transmogrifier.sitewalker
    start-path = /oxfam
    limit = 1000

The ``[schemadumper]`` section controls the way in which the schema of objects
is converted to a csv row. You may provide a list of fields to exclude. If the
named field exists in an object's schema, it will be left out of the final csv
file for that type.  This can be used to control the volume of data dumped:

    [schemadumper]
    blueprint = oxfama.transmogrifier.schemadumper
    exclude =
        text
        description
        file
        image

The ``[writer]`` section controls the writing of csv files to the filesystem.
There are no settings currently available for this section.

The ``[logger]`` section controls the writing of log output for each object
as it is passed through the pipeline.  You can provide a list of the *keys*
for each item that will be written to the log line.  

To omit any section, simply remove its name from the ``pipeline`` setting in 
the ``[transmogrifier]`` section of the configuration file.

