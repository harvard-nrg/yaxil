YAXIL: Yet another XNAT interface library
=========================================
Yaxil is an XNAT interface library that started a long time ago in a galaxy far, 
far away. It works with Python 2 and 3 and XNAT 1.4 through 1.7. There are 
very simple functions for querying XNAT, searching for MRI scans, downloading 
imaging data, and it smooths over various aches and pains. I know the world was 
not in need of yet another XNAT library, but it's all good.

## Table of contents
1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Documentation](#documentation)
4. [Example usage](#example-usage)

## Requirements
Works with Python 2 and 3 on Linux and macOS (at least that's the goal).

## Installation
Most of the time you'll want to use `pip`

```bash
pip install yaxil
```

## Documentation
Full documentation can be found at <http://yaxil.readthedocs.io/>.

## Example usage
There are all sorts of functions in `yaxil` that help you get what you need from 
XNAT with a `requests`-like feel and some safety nets.

You can use `yaxil` to resolve the unique XNAT Accession ID for a given MR 
Session Label and be warned of any collisions

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

Then you can query for the scans you need by supplying a `dict` of SQL 
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

Then you can download your scans from XNAT

```python
>>> yaxil.download(auth, aid, [11, 12, 14], out_dir='./dicomz')
```

And finally you can import `yaxil.dicom` to index your downloaded DICOM files 
and do things with them

```python
import yaxil.dicom

index = yaxil.dicom.search('./dicomz')

for study,series in iter(index.items()):
  print("Study {0}".format(study))
  for series,instances in iter(series.items()):
    print("  Series {0}".format(series))
    for instance,files in iter(instances.items()):
      print("    Instance {0}".format(instance))
      for f in files:
        print("     File {0}".format(f.file))
```

things like this.
