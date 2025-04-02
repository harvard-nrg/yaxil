.. _arcget:

ArcGet.py: yet another XNAT command line downloader
===================================================

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

Direct export to BIDS (beta)
----------------------------
.. note::
   BIDS support is a work in progress. If you're interested in contributing, feel 
   free to fork the project and submit a pull request 🚀.

As you know, ``ArcGet.py`` will download your data into a unstructured 
directory by default. While this is certainly useful, 
`BIDS <http://bids.neuroimaging.io/>`_ 
has become a widely accepted standard for organizing neuroimaging data.

``ArcGet.py`` includes functionality to download and save your data directly 
in BIDS format by way of a simple (cough) YAML configuation file. Below you'll 
find an example configuration file that includes almost every type of scan 
that's been thrown at ``ArcGet.py``. This should get you started

.. note::
   I chose YAML because there's less syntax than, say,  XML or JSON. However, 
   there is still *some* syntax to familiarize yourself with. In particular, 
   whitespace is syntactically important. YAML uses space characters, not tabs, 
   to indicate nesting. This is a common place to get tripped up.

.. code-block:: yaml

  anat:
      T1w:
          - scan: 6
            run: 1
      T2w:
          - scan: 7
            run: 1
  func:
      bold:
          - scan: 11
            task: LANG
            run: 1
            task: lang1
          - scan: 13
            run: 2
            task: LANG
            id: lang2
          - scan: 15
            task: REST
            direction: ap
            run: 1
            id: rest_ap
      sbref:
          - scan: 10
            run: 1
            task: LANG
          - scan: 12
            run: 2
            task: LANG
  fmap:
      magnitude:
          - scan: 40
            run: 1
            direction: ap
            intended for:
              - lang1
              - lang2
      epi:
          - scan: 43
            run: 1
            direction: ap
            intended for:
              - rest_ap
          - scan: 44
            run: 1
            direction: pa
            acquisition: CMRRABCDb0
            intended for:
              - CMRRABCDd102
      phasediff:
          - scan: 34
            run: 1
  dwi:
      sbref:
          - scan: 45
            run: 1
            direction: ap
          - scan: 44
            run: 1
            direction: pa
      dwi:
          - scan: 46
            run: 1
            direction: ap
            acquisition: CMRRABCDd102
            id: CMRRABCDd102  
          - scan: 49
            run: 1 
            direction: pa

If you're familiar with the 
`BIDS specification <https://bids-specification.readthedocs.io/en/stable/>`_,
the field names in the configuration file shown above should be fairly 
self-explanatory. Note that I chose to use expanded field names for the sake 
of readability. For example, instead of ``dir`` I chose ``direction`` and 
instead of ``acq`` I chose ``acquisition``. Readability is good.

IntendedFor 
^^^^^^^^^^^
The only tricky part is how to explain to ``ArcGet.py`` how it should insert 
the ``IntendedFor`` into the ``fmap`` JSON sidecar files. Here's how that works. 
For any ``fmap`` scan declared in your configuration file, you can insert an 
``intended for`` field, followed by a list of references to any ``id`` fields 
for any other scan. There are several examples of this in the configuration 
file shown above.

Usage
^^^^^
When you pass this configuration file to ``ArcGet.py``, you should end up with 
your data downloaded and converted into a proper BIDS structure

.. code-block:: python

  ArcGet.py -a xnatastic -s <session> -c bids.yaml -f bids -o ./bids

Enjoy.
