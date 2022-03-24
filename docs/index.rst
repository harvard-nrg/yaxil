.. yaxil documentation master file, created by
   sphinx-quickstart on Fri Oct  5 10:31:38 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

YAXIL: yet another XNAT interface library
=========================================

Yaxil is an XNAT interface library that started a long time ago in a galaxy 
far, far away. It works with Python 3 and XNAT 1.4 through 1.8.

Here's a basic example of YAXIL in action

.. code-block:: python

  import os
  import yaxil

  auth = yaxil.XnatAuth(url='https://xnatastic.org', username='you', password='*****')

  with yaxil.session(auth) as sess:
    # get all subjects for given project
    for subject in sess.subjects(project='PROJECT'):
      # get all MRIs for the given subject
      for experiment in sess.experiments(subject=subject):
        # get all scans for the given experiment
        for scan in sess.scans(experiment=experiment):
          # download scans with note 'REST1', 'REST2', or 'ANAT1'
          if scan['note'] in ('REST1', 'REST2', 'ANAT1'):
            sid = scan['id']
            outdir = os.path.join(subject.label, experiment.label, sid)
            sess.download(experiment.label, [sid], out_dir=outdir)

Huzzah! There are many more functions and tools for accessing your subject, 
experiment, and scan metadata. Head over to the API reference for more.

API Reference
-------------

If you're looking for information on a specific API function, look no further

.. toctree::
   :maxdepth: 2

   api

ArcGet.py
---------

If you're looking for information about ``ArcGet.py``, you're going to like this

.. toctree::
   :maxdepth: 2

   arcget

xnat_auth
---------

Here's a quick and dirty command line tool to help you set up an 
``~/.xnat_auth`` file

.. toctree::
   :maxdepth: 2

   xnat_auth

