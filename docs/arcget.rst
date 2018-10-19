.. _arcget

ArcGet.py: yet another XNAT command line downloader
===================================================

-----------------------------------------

The standard XNAT distribution provides a command line tool called ``ArcGet`` 
to help you download your data from XNAT to your local hard drive. The YAXIL 
version of ``ArcGet.py`` does the same thing, but with a few extra nuggets.

Basic Usage
-----------
If you want to download all scans for a MR Session, use this

.. code-block:: bash

  ArcGet.py -a xnatastic -s LABEL -o ./dicoms

If you know the scan numbers that you want to download, use the ``-r|--scans`` 
argument

.. code-block:: bash

  ArcGet.py -a xnatastic -s LABEL -r 1 2 3 -o ./dicoms

If you know the scan types that you want to download, use the ``-t|--types`` 
argument

.. code-block:: bash

  ArcGet.py -a xnatastic -s LABEL -t MEMPRAGE BOLD --output-dir ./dicoms

If you know the tasks that were coded into the XNAT scan notes field, use the 
``-k|--tasks`` argument

.. code-block:: bash

  ArcGet.py -a xnatastic -s LABEL -k ANAT1 REST1 -o ./dicoms

This functionality should more or less cover what you already know and love from 
classic ``ArcGet``.

BIDS compatibility
------------------
By default ``ArcGet.py`` will download your data into a flat unstructured 
directory. This is nice, but there is a new standard in town when it comes to 
organizing your neuroimaging data on disk called 
`BIDS <http://bids.neuroimaging.io/>`_.

The BIDS specification is long, but in short BIDS wants you to store your 
functional scans in a ``func`` folder, your anatomical scans in an ``anat`` 
folder, your field distortion maps in a ``fmap`` folder, and so on. BIDS also 
wants you to convert your files to NIFTI format and name your files with 
important pieces of information such as the ``subject``, ``session``, ``task``, 
``run``, and so forth. You can read up on the full specification 
`here <http://bids.neuroimaging.io/bids_spec.pdf>`_.

The YAXIL version of ``ArcGet.py`` will help you download and save your data 
into a proper BIDS structure in two ways. The first way is by supplying a very 
simple, MR Session specific configuation file in fabulous YAML format. Here is 
an example

.. code-block:: yaml

  func:
    bold:
      - scan: 12
        task: REST
        run: 1
      - scan: 16
        task: REST
        run: 2
      - scan: 28
        task: LANG
        run: 1
      - scan: 30
        task: LANG
        run: 2
  fmap:
    magnitude1:
      - scan: 33
        run: 1
  anat:
    T1w:
      - scan: 10
        run: 1
      - scan: 36
        run: 2  

When you pass this file to ``ArcGet.py``, you will end up with your data 
downloaded and converted to a proper BIDS structure

.. code-block:: python

  ArcGet.py -a xnatastic -s LABEL -c bids_me.yaml -o ./bids

Huzzah!

``ArcGet.py`` also supports a second way to output your data to a BIDS 
structure that does not require any configuration file. ``ArcGet.py`` will use 
a combination of XNAT metadata and additional information coded into the scan 
``note`` field to make sense of your data. If you set your scan note field(s) 
to ``ANAT_001``, ``REST_001``, ``REST_002``, ``FMAPM_001``, these strings will 
be parsed and used to construct a proper BIDS structure

.. code-block:: python

  ArcGet.py -a xnatastic -s LABEL -k ANAT_001 REST_001 REST_002 FMAPM_001 -b -o ./bids

Internally, the ``-b|--bids`` argument will basically construct a configuration 
file similar to the one described above using your XNAT database.

