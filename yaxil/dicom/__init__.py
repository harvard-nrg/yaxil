import os
import pydicom
import logging
import collections as col

logger = logging.getLogger(__name__)

DicomFile = col.namedtuple('DcmFile', ['meta', 'file'])
'''
DICOM file container. Contains fields for metadata (header data) and the file 
location.
'''

def search(d, recursive=True, store_meta=True):
    '''
    Search for DICOM files within a given directory and receive back a 
    dictionary of {StudyInstanceUID: {SeriesNumber: [files]}}
    
    Example usage::
        >>> import yaxil.dicom
        >>> yaxil.dicom.search("~/dicoms").keys()
        ['1.2.340.500067.8.9.10.11012.13000001401516017181900000200']
        
    :param d: Directory name
    :type d: str
    :param recursive: Search recursively
    :type recursive: bool
    :param store_meta: Read and store metadata for each file for fast lookups
    :type store_meta: bool
    :returns: Dictionary of {StudyInstanceUID: {SeriesNumber: [files]}}
    :rtype: dict
    '''
    # say this fast three times
    scans = col.defaultdict(lambda: col.defaultdict(lambda: col.defaultdict(list)))
    for dirpath,dirnames,filenames in os.walk(os.path.expanduser(d)):
        for f in filenames:
            fullfile = os.path.join(dirpath, f)
            try:
                d = pydicom.read_file(fullfile, stop_before_pixels=True)
            except pydicom.filereader.InvalidDicomError:
                continue
            meta = {k: getattr(d, k, None) for k in d.dir()} if store_meta else None
            scans[d.StudyInstanceUID][d.SeriesNumber][d.InstanceNumber].append(DicomFile(meta=meta, file=fullfile))
        if not recursive:
            del dirnames[:]
    return scans

