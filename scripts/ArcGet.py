#!/usr/bin/env python

import os
import re
import sys
import csv
import six
import json
import yaml
import yaxil
import string
import logging
import tarfile
import argparse as ap
import tempfile as tf
import subprocess as sp
import collections as col
import yaxil.bids as bids
import yaxil.commons as commons

logger = logging.getLogger(__file__)

def main():
    # parse arguments and configure logging
    args = parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # --session deprecation warning
    if args.session:
        logger.warn('DEPRECATION WARNING: use -l|--label instead of -s|--session')
        args.label = args.session

    # --raw-types deprecation warning
    if args.raw_types:
        logger.warn('DEPRECATION WARNING: use --scans instead of -r|--raw-types')
        args.scans = args.raw_types

    # --bids deprecation warning
    if args.bids:
        logger.warn('DEPRECATION WARNING: use -o|--output-format bids instead of --bids')
        args.output_format = 'bids'

    args.output_dir = os.path.expanduser(args.output_dir)

    # append additional XNAT 1.4 directories to output directory
    if args.output_format == '1.4':
        args.output_dir = os.path.join(args.output_dir, args.label, 'RAW')

    if args.insecure:
        yaxil.CHECK_CERTIFICATE = False

    auth = yaxil.auth2(args.alias, args.host, args.username, args.password)

    # print readme and exit
    if args.readme:
        content = readme(auth, args.label, args.project)
        print(content)
        sys.exit(0)

    # to maintain backwards compatibility, split -r, -c, or -k arguments
    # that are comma-separated
    args.scans = splitarg(args.scans)
    args.types = splitarg(args.types)
    args.tasks = splitarg(args.tasks)

    # this command line tool is needed for bids-ification, check for it now
    if args.output_format == 'bids':
        dcm2niix = commons.which('dcm2niix')
        if not dcm2niix:
            raise Exception('could not find dcm2niix')

    with yaxil.session(auth) as sess:
        # request all scan metadata for this mr session
        scans_meta = list(sess.scans(args.label, project=args.project))
        # download all scans if no scans, types, or tasks were requested
        scan_ids = [x['id'] for x in scans_meta if x['id']]
        if not args.scans and not args.types and not args.tasks:
            args.scans = scan_ids
        # read bids configuration file, or use command line arguments
        if args.config:
            logger.debug('reading bids configuration from %s', args.config)
            config = yaml.load(args.config, Loader=yaml.FullLoader)
            bids.bids_from_config(sess, scans_meta, config, args.output_dir)
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
            if args.output_format == 'bids':
                config = generate_bids_config(download)
                bids.bids_from_config(sess, scans_meta, config, args.output_dir)
            else:
                scan_ids = sorted(download.keys(), key=int)
                logger.info('downloading scans %s', ','.join(scan_ids))
                sess.download(args.label, scan_ids, project=args.project,
                              out_dir=args.output_dir, progress=1024**2,
                              attempts=3, out_format=args.output_format)

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
        elif re.match('[#]?ANAT_T2*', scan_meta['note']):
            type_ = 'anat'
            modality = 'T2w'
        elif scan_meta['note'].startswith('ANAT'):
            type_ = 'anat'
            modality = 'T1w'
        elif scan_meta['note'].startswith('FMAPM'):
            type_ = 'fmap'
            modality = 'magnitude'
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

def find(scans_mdata, targets, key):
    info = dict()
    for scan_mdata in scans_mdata:
        if scan_mdata[key] in targets:
            info[scan_mdata['id']] = scan_mdata
    return info

def splitarg(args):
    '''
    This function will split arguments separated by spaces or commas
    to be backwards compatible with the original ArcGet command line tool
    '''
    if not args:
        return args
    split = list()
    for arg in args:
        if ',' in arg:
            split.extend([x for x in arg.split(',') if x])
        elif arg:
            split.append(arg)
    return split

def readme(auth, label, project=None):
    sio = six.StringIO()
    writer = csv.writer(sio)
    writer.writerow(['scan', 'type', 'series', 'quality', 'note'])
    scans = yaxil.scans(auth, label=label, project=project)
    for scan in sorted(scans, key=lambda x: int(x['id'])):
        num = scan['id']
        series = scan['series_description']
        stype = scan['type']
        quality = scan['quality']
        note = scan['note']
        writer.writerow([num, stype, series, quality, note])
    sio.seek(0)
    return sio.read()

def parse_args():
    parser = ap.ArgumentParser('Huzzah! Yet another XNAT downloader.')
    parser.add_argument('-a', '--alias',
        help='XNAT alias within ~/.xnat_auth')
    parser.add_argument('-host', '--host',
        help='XNAT host')
    parser.add_argument('--username',
        help='XNAT username')
    parser.add_argument('--password',
        help='XNAT password')
    group_a = parser.add_mutually_exclusive_group(required=True)
    group_a.add_argument('-l', '--label',
        help='XNAT Session Label')
    group_a.add_argument('-s', '--session',
        help='Same as --label (deprecated)')
    parser.add_argument('-p', '--project',
        help='XNAT Session Project')
    group_b = parser.add_mutually_exclusive_group()
    group_b.add_argument('--scans', nargs='+',
        help='Raw scans numbers')
    group_b.add_argument('-r', '--raw-types', nargs='+',
        help='Same as --scans (deprecated)')
    parser.add_argument('-c', '--config', type=ap.FileType('r'),
        help='BIDS configuration')
    parser.add_argument('-t', '--types', nargs='+',
        help='Scans types')
    parser.add_argument('-k', '--tasks', nargs='+',
        help='Scans tasks(notes)')
    parser.add_argument('--insecure', action='store_true',
        help='Turn off SSL certificate checking (needed for tunneled connections)')
    parser.add_argument('-o', '--output-dir', '--out-dir', default='.',
        help='Output directory')
    parser.add_argument('-f', '--output-format', choices=['1.4', 'bids', 'flat', 'native'], default='1.4',
        help='Output directory format')
    parser.add_argument('--bids', action='store_true',
        help='Output in BIDS format (same as --output-format=bids)')
    parser.add_argument('--readme', action='store_true',
        help='Output scan summary in parsable format')
    parser.add_argument('--debug', action='store_true',
        help='Enable debug messages')
    return parser.parse_args()

if __name__ == '__main__':
    main()
