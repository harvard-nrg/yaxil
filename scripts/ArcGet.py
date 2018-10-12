#!/usr/bin/env python

import os
import re
import sys
import json
import yaxil
import logging
import tarfile
import argparse
import tempfile as tf
import subprocess as sp
import yaxil.commons as commons

logger = logging.getLogger(__file__)
logging.getLogger('vcr').setLevel(logging.WARNING)

def main():
    parser = argparse.ArgumentParser('Huzzah! Yet another XNAT downloader.')
    group_a = parser.add_mutually_exclusive_group(required=True)
    group_a.add_argument('-a', '--alias',
        help='XNAT alias within ~/.xnat_auth')
    group_a.add_argument('-host',
        help='XNAT url within ~/.xnat_auth')
    parser.add_argument('-l', '--label', '-s', '--session', required=True,
        help='XNAT Session Label')
    parser.add_argument('-p', '--project',
        help='XNAT Session Project')
    parser.add_argument('-r', '--scans', nargs='+',
        help='Raw scans numbers')
    parser.add_argument('-t', '--types', nargs='+',
        help='Scans types')
    parser.add_argument('-k', '--tasks', nargs='+',
        help='Scans tasks(notes)')
    parser.add_argument('--insecure', action='store_true',
        help='Turn off SSL certificate checking (needed for tunneled connections)')
    parser.add_argument('-o', '--output-dir', default='.',
        help='Output directory')
    parser.add_argument('-b', '--bids', action='store_true',
        help='BIDS output directory structure')
    parser.add_argument('--debug', action='store_true',
        help='Enable debug messages')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    args.output_dir = os.path.expanduser(args.output_dir)

    if args.insecure:
        yaxil.CHECK_CERTIFICATE = False

    if args.alias:
        auth = yaxil.auth(args.alias)
    elif args.host:
        auth = yaxil.auth(url=args.host)

    if args.bids:
        dcm2niix = which('dcm2niix')
        if not dcm2niix:
            raise Exception('could not find dcm2niix')

    with yaxil.session(auth) as sess:
        download = dict()
        scans_mdata = list(sess.scans(args.label, args.project))
        # resolve scan ids
        if args.scans:
            download.update(find(scans_mdata, targets=args.scans, key='id'))
        # resolve types to scan numbers
        if args.types:
            download.update(find(scans_mdata, targets=args.types, key='type'))
        # resolve tasks to scan numbers
        if args.tasks:
            download.update(find(scans_mdata, targets=args.tasks, key='note'))
        # download to flat directory or to a bids hierarchy
        if args.bids:
            logger.info('downloading scans: %s', ','.join(download.keys()))
            bids(sess, download, args.output_dir)
        else:
            logger.info('downloading scans: %s', ','.join(download.keys()))
            sess.download(args.label, download.keys(), project=args.project,
                          out_dir=args.output_dir, progress=1024**2,
                          attempts=3)

def bids(sess, download, out_base, sourcedata=True):
    # get session and subject labels
    item = next(iter(download.values()))
    session,subject = item['session_label'], item['subject_label']
    # bids and sourcedata base directories
    sdata_base = os.path.join(out_base, 'sourcedata',
                              'sub-{0}'.format(subject),
                              'ses-{0}'.format(session))
    bids_base = os.path.join(out_base,
                              'sub-{0}'.format(subject),
                              'ses-{0}'.format(session))
    # process each scan
    for scan_id,mdata in iter(download.items()):
        info = heuristic(mdata)
        # file base
        fbase = 'sub-{sub}_ses-{ses}_task-{task}_{subtype}'
        fbase = fbase.format(sub=subject,
                             ses=session,
                             task=info['task'],
                             subtype=info['sub_type'])
        # download raw data
        sdata_dir = os.path.join(sdata_base, info['data_type'])
        if not os.path.exists(sdata_dir):
            os.makedirs(sdata_dir)
        dicom_dir = os.path.join(sdata_dir, '{0}.dicom'.format(fbase))
        logger.info('downloading session=%s, scan=%s, loc=%s', session, scan_id, dicom_dir)
        sess.download(session, [scan_id], out_dir=dicom_dir)
        # convert to nifti1-gz
        fname = '{0}.nii.gz'.format(fbase)
        fullfile = os.path.join(bids_base, info['data_type'], fname)
        convert(dicom_dir, fullfile)

def convert(input, output):
    dirname = os.path.dirname(output)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    basename = os.path.basename(output)
    basename = re.sub('.nii(.gz)?', '', basename)
    cmd = [
        'dcm2niix',
        '-b', 'y',
        '-z', 'y',
        '-f', basename,
        '-o', dirname,
        input
    ]
    logger.info(cmd)
    sp.check_output(cmd)

def heuristic(mdata):
    '''
    This is similar to heudiconv infodict
    '''
    scan_type,note = mdata['type'], mdata['note']
    info = {
        'data_type': None,
        'sub_type': None,
        'task': note if note else 'unknown'
    }
    if scan_type == 'BOLD':
        info['data_type'] = 'func'
        info['sub_type']  = 'bold'
    elif scan_type.startswith('MEMPRAGE') or \
            note.startswith('ANAT'):
        info['data_type'] = 'anat'
        info['sub_type']  = 'T1w'
    elif scan_type.startswith('BOLDFMAP'):
        info['data_type'] = 'fmap'
        info['sub_type']  = 'magnitude1'
    elif scan_type == 'DWI':
        info['data_type'] = 'dwi'
        info['sub_type']  = 'dwi'
    else:
        raise DataTypeError('cannot determine bids data type for scan %s', mdata['id'])
    return info

class DataTypeError(Exception):
    pass

def find(scans_mdata, targets, key):
    info = dict()
    for scan_mdata in scans_mdata:
        if scan_mdata[key] in targets:
            info[scan_mdata['id']] = scan_mdata
    return info

def which(x):
    for p in os.environ.get('PATH').split(os.pathsep):
        p = os.path.join(p, x)
        if os.path.exists(p):
            return os.path.abspath(p)
    return None

if __name__ == '__main__':
    main()

