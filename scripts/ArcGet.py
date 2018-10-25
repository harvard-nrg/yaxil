#!/usr/bin/env python

import os
import re
import sys
import json
import yaml
import yaxil
import string
import logging
import tarfile
import argparse
import tempfile as tf
import subprocess as sp
import collections as col
import yaxil.commons as commons

logger = logging.getLogger(__file__)

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
    parser.add_argument('-c', '--config',
        help='BIDS configuration')
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

    # this command line tool is needed for bids-ification
    if args.bids:
        dcm2niix = which('dcm2niix')
        if not dcm2niix:
            raise Exception('could not find dcm2niix')

    with yaxil.session(auth) as sess:
        # request all scan metadata for this mr session
        scans_meta = list(sess.scans(args.label, args.project))
        # download all scans if no scans, types, or tasks were requested
        scan_ids = [x['id'] for x in scans_meta if x['id']]
        if not args.scans and not args.types and not args.tasks:
            args.scans = scan_ids
        # read bids configuration file, or use command line arguments
        if args.config:
            with open(args.config, 'r') as fo:
                config = yaml.load(fo)
            bids_from_config(sess, scans_meta, config, args.output_dir)
        else:
            download = dict()
            # resolve scans by ids
            if args.scans:
                download.update(find(scans_meta, targets=args.scans, key='id'))
            # resolve scans by types
            if args.types:
                download.update(find(scans_meta, targets=args.types, key='type'))
            # resolve scans by notes
            if args.tasks:
                download.update(find(scans_meta, targets=args.tasks, key='note'))
            # quit if no scans were found to download
            if not download:
                logger.critical('no scans found to download')
                sys.exit(1)
            # download data to a flat directory or output to a bids structure
            if args.bids:
                config = generate_bids_config(download)
                bids_from_config(sess, scans_meta, config, args.output_dir)
            else:
                scan_ids = sorted(download.keys(), key=int)
                logger.info('downloading scans %s', ','.join(scan_ids))
                sess.download(args.label, scan_ids, project=args.project,
                              out_dir=args.output_dir, progress=1024**2,
                              attempts=3)

def generate_bids_config(scans):
    config = col.defaultdict(lambda: col.defaultdict(list))
    regex = re.compile('([a-zA-Z]+)_?(\d+)?')
    for scan_id,scan_meta in iter(scans.items()):
        note = scan_meta['note']
        match = regex.match(note)
        if not match:
            raise ConfigGeneratorError('failed to parse note ({0}) for scan {1}'.format(note, scan_id))
        task,run = match.groups('1')
        # this will certainly need to be extended over time
        if scan_meta['type'] == 'BOLD':
            type_ = 'func'
            modality = 'bold'
        elif scan_meta['note'].startswith('ANAT'):
            type_ = 'anat'
            modality = 'T1w'
        elif scan_meta['note'].startswith('FMAPM'):
            type_ = 'fmap'
            modality = 'magnitude1'
        elif scan_meta['note'].startswith('FMAPP'):
            type_ = 'fmap'
            modality = 'phasediff'
        else:
            raise ConfigGeneratorError('could not determine type or modality for scan {0}'.format(scan_id))
        config[type_][modality].append({
            'scan': scan_id,
            'task': task,
            'run': run
        })
    return config

class ConfigGeneratorError(Exception):
    pass

def bids_from_config(sess, scans_metadata, config, out_base):
    # bids legal characters for sub, ses, task
    legal = re.compile('[^a-zA-Z0-9]')
    # get session and subject labels
    item = next(iter(scans_metadata))
    session,subject = item['session_label'],item['subject_label']
    # bids and sourcedata base directories
    sdata_base = os.path.join(out_base, 'sourcedata',
                              'sub-{0}'.format(legal.sub('', subject)),
                              'ses-{0}'.format(legal.sub('', session)))
    bids_base = os.path.join(out_base,
                              'sub-{0}'.format(legal.sub('', subject)),
                              'ses-{0}'.format(legal.sub('', session)))
    # iterate over config
    for scan in iterconfig(config):
        if scan['type'] == 'func':
            fbase = string.Template('sub-${sub}_ses-${ses}_task-${task}_run-${run}_${modality}')
        elif scan['type'] == 'anat':
            fbase = string.Template('sub-${sub}_ses-${ses}_run-${run}_${modality}')
        elif scan['type'] == 'fmap':
            fbase = string.Template('sub-${sub}_ses-${ses}_run-${run}_${modality}')
        fbase = fbase.safe_substitute(
            sub=legal.sub('', subject),
            ses=legal.sub('', session),
            run=scan.get('run', None),
            modality=scan.get('modality', None),
            task=scan.get('task', None)
        )
        # download data to bids sourcedata directory
        sourcedata_dir = os.path.join(sdata_base, scan['type'])
        if not os.path.exists(sourcedata_dir):
            os.makedirs(sourcedata_dir)
        dicom_dir = os.path.join(sourcedata_dir, '{0}.dicom'.format(fbase))
        logger.info('downloading session=%s, scan=%s, loc=%s', session, scan['scan'], dicom_dir)
        sess.download(session, [scan['scan']], out_dir=dicom_dir)
        # convert to nifti1-gz
        fname = '{0}.nii.gz'.format(fbase)
        fullfile = os.path.join(bids_base, scan['type'], fname)
        convert(dicom_dir, fullfile)

def iterconfig(config):
    for type_,modalities in iter(config.items()):
        for modality,scans in iter(modalities.items()):
            for scan in scans:
                scan.update({
                    'type': type_,
                    'modality': modality
                })
                yield scan

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

