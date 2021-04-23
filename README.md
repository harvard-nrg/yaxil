YAXIL: Yet another XNAT interface library
=========================================
Yaxil is an XNAT interface library that started a long time ago in a galaxy far, 
far away. It works with Python 2 and 3 and XNAT 1.4 through 1.8. There are 
simple functions for querying XNAT, searching for MRI scans, downloading scan 
data, all while smoothing over various aches and pains along the way.

## Table of contents
1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Documentation](#documentation)

See full documentation at <http://yaxil.readthedocs.io/>.

## Requirements
Works with Python 2 and 3 on Linux and macOS.

## Installation
Most of the time you'll want to use `pip`

```bash
pip install yaxil
```

Once that's done, you need to create an ~/.xnat_auth file, and you should be ready to go!

```
<xnat>
    <cbscentral version="1.5">
    <url>https://cbscentral.rc.fas.harvard.edu</url>
    <username>MJbball1991</username>
    <password>DaBullsDaBullsDaBullsDaBulls</password>
    </cbscentral>
</xnat>
```

## Documentation
Full documentation can be found at <http://yaxil.readthedocs.io/>.

