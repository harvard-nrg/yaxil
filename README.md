YAXIL: Yet another XNAT interface library
=========================================
Yaxil was (and still is) an internally developed XNAT interface library that 
started a long time ago in a galaxy far, far away. It works with Python 2 and 
3 and XNAT 1.4 through 1.7. It smooths over some aches and pains. I know the 
world was not in need of yet another XNAT library, but it's all good.

## Table of contents
1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Basic usage](#basic-usage)

## Requirements
Works with Python 2 and 3 on Linux and macOS (at least that's the goal).

## Installation
Most of the time you'll want to use `pip`

```bash
pip install yaxil
```

## Basic usage
There are all sorts of functions in `yaxil` that help you get what you need from 
XNAT with a `requests`-like feel and some safety nets

```python
>>> import yaxil
>>> auth = yaxil.XnatAuth(url='https://xnatastic.org', username='foobar', password='******')
>>> aid = yaxil.accession(auth, 'MR_SESSION_LABEL')
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "yaxil/__init__.py", line 245, in accession
    return experiment(auth, label, project).id
  File "yaxil/__init__.py", line 214, in experiment
    "for label %s" % label)
yaxil.MultipleAccessionError: too many accession ids returned for label MR_SESSION_LABEL
>>> aid = yaxil.accession(auth, 'MR_SESSION_LABEL', project='ProjectA')
```

You can also use `yaxil` to download data from XNAT

```python
>>> yaxil.download(auth, aid, [11, 12, 14], out_dir='./dicomz')
```

You can also query for scans by supplying a `dict` of keys and corresponding SQL 
conditions

```python
>>> query = {
...   'anat': 'note == "ANAT1"',
...   'rest1_fmap': 'series_description LIKE "BOLDFMAP_2p4mm_65sl%"',
...   'rest1_bold': 'note == "REST1"'
... }
>>> scans = yaxil.scansearch(auth, aid, query)
>>> print(json.dumps(scans, indent=2))
{
  "rest1_fmap": [
    14
  ], 
  "rest1_bold": [
    12
  ], 
  "anat": [
    11
  ]
}
```

things like this.

