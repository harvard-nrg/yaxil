.. yaxil documentation master file, created by
   sphinx-quickstart on Fri Oct  5 10:31:38 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

YAXIL: yet another XNAT interface library
=========================================

-----------------------------------------

Yaxil is an XNAT interface library that started a long time ago in a galaxy far, 
far away. It works with Python 2 and 3 and XNAT 1.4 through 1.7. This 
documentation covers all of the functions and classes in YAXIL and examples 
to help you get going.

Here's an example of YAXIL in action

.. code-block:: python

  import yaxil
  
  auth = yaxil.XnatAuth(url='https://xnatastic.org', username='you', password='*****')
  query = {
      'anat': 'note == "ANAT1"'
  }
  scans = yaxil.scansearch(auth, 'MR_SESSION_LABEL', query)
  yaxil.download(auth, 'MR_SESSION_LABEL', scans['anat'], out_dir='./dicomz')

Or you can avoid explicitly passing ``auth`` to every function by using a 
``session`` context

.. code-block:: python

  import yaxil
  
  auth = yaxil.XnatAuth(url='https://xnatastic.org', username='you', password='*****')

  with yaxil.session(auth) as sess:
    query = {
        'anat': 'note == "ANAT1"'
    }
    scans = sess.scansearch('MR_SESSION_LABEL', query)
    sess.download('MR_SESSION_LABEL', scans['anat'], out_dir='./dicomz')

Huzzah! There are many more functions for accessing your scan metadata, 
experiment metadata, subject metadata, and more. Every documented function 
contains a example usage.

The API Documentation / Guide
-----------------------------

If you are looking for information on a specific function, read this

.. toctree::
   :maxdepth: 2

   api

ArcGet.py Guide
---------------

If you're looking for information about ``ArcGet.py`` look no further

.. toctree::
   :maxdepth: 2

   arcget
