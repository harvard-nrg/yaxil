.. _arcget

ArcGet.py: yet another XNAT command line downloader
===================================================

-----------------------------------------

The standard XNAT distribution provides a simple command line tool called 
``ArcGet`` that helps you download your imaging data from XNAT to your local 
hard drive. Not surprisingly, the YAXIL version of ``ArcGet.py`` does pretty 
much the same thing, but with a few extra useful nuggets.

Basic Usage
-----------
If you want to download all scans for a MR Session, just use this

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

If you know the tasks that were coded into the scan notes field, use the 
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

To be brief, the BIDS specification wants you to store your functional scans in 
a ``func`` folder, your anatomical scans in an ``anat`` folder, your field 
distortion maps in a ``fmap`` folder, and so on. BIDS also wants you to convert 
your files to NIFTI format and name your files with useful pieces of information 
such as the ``subject``, ``session``, ``task``, ``run``, etc. You can read up on 
the full specification `here <http://bids.neuroimaging.io/bids_spec.pdf>`_.

The YAXIL version of ``ArcGet.py`` will help you download and save your data 
into a proper BIDS structure in two ways. The first way involves supplying a 
simple YAML formatted configuation file. Here is an example

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
structure that does not require a configuration file. By supplying the 
``-b|--bids`` argument, ``ArcGet.py`` will use XNAT scan metadata and 
additional information coded into the scan ``note`` field. If you set 
your scan note field(s) to ``ANAT_001``, ``REST_001``, ``REST_002``, 
``FMAPM_001``, etc. these strings will be parsed and used to construct 
a proper BIDS structure

.. code-block:: python

  ArcGet.py -a xnatastic -s LABEL -k ANAT_001 REST_001 REST_002 FMAPM_001 -b -o ./bids

Internally, the ``-b|--bids`` argument will construct a configuration 
file similar to the one described above.

