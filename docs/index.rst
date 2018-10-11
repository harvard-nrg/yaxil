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
  aid = yaxil.accession(auth, 'AB1234C')
  query = {
      'anat': 'note == "ANAT1"'
  }
  scans = yaxil.scansearch(auth, aid, query)
  yaxil.download(auth, aid, scans['anat'], out_dir='dicomz')

Or you can ditch explicitly passing ``auth`` to every function and just use 
a ``session`` context

.. code-block:: python

  import yaxil
  
  auth = yaxil.XnatAuth(url='https://xnatastic.org', username='you', password='*****')

  with yaxil.session(auth) as sess:
    aid = sess.accession('AB123C')
    query = {
        'anat': 'note == "ANAT1"'
    }
    scans = sess.scansearch(aid, query)
    sess.download(aid, scans['anat'], out_dir='dicomz')

Huzzah!!

The API Documentation / Guide
-----------------------------

If you are looking for information on a specific function, read this

.. toctree::
   :maxdepth: 2

   api
