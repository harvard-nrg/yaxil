#!/usr/bin/env python

import os
import sys
import json
import yaxil
import logging
import argparse
import yaxil.commons as commons

logger = logging.getLogger(__file__)

def main():
    parser = argparse.ArgumentParser('Huzzah! Another XNAT downloader script.')
    parser.add_argument('-a', '--alias', required=True, 
        help='XNAT alias')
    parser.add_argument('-l', '--label', required=True, 
        help='XNAT Session Label')
    parser.add_argument('-p', '--project', 
        help='XNAT Session Project')
    parser.add_argument('-s', '--scans', nargs='+', 
        help='Raw scans numbers')
    parser.add_argument('-t', '--types', nargs='+', 
        help='Scans types')
    parser.add_argument('-k', '--tasks', nargs='+', 
        help='Scans tasks(notes)')
    parser.add_argument('--insecure', action='store_true', 
        help='Turn off SSL certificate checking (needed for tunneled connections)')
    parser.add_argument('-o', '--output-dir', default='.', 
        help='Output directory')
    parser.add_argument('--dry-run', action='store_true',
        help='Print scants that would be downloaded, but do not download')
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

    auth = yaxil.auth(args.alias)

    with yaxil.session(auth) as sess:
        scan_ids = set(args.scans)
        # resolve types to scan numbers
        if args.types:
            scan_ids.update(resolve(sess, args.label, args.project, 
                                    targets=args.types, key='type'))
        # resolve tasks to scan numbers
        if args.tasks:
            scan_ids.update(resolve(sess, args.label, args.project, 
                                    targets=args.tasks, key='note'))
        # download
        logger.info('downloading scans %s', list(scan_ids))
        if not args.dry_run:
            sess.download(args.label, scan_ids, project=args.project,
                          out_dir=args.output_dir, progress=1024**2,
                          attempts=3)

def resolve(sess, label, project, targets, key):
    scans = list()
    for scan in sess.scans(label, project=project):
        if scan[key] in targets:
            scans.append(scan['id'])
    return scans

if __name__ == '__main__':
    main()

