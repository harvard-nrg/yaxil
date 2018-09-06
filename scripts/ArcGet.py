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
        help='Scans numbers filter')
    parser.add_argument('--insecure', action='store_true', 
        help='Turn off SSL certificate checking (needed for tunneled connections)')
    parser.add_argument('--scan-only', action='store_true', 
        help='Print scan information only')
    parser.add_argument('-o', '--output-dir', default='.', 
        help='Output directory')
    parser.add_argument('--debug', action='store_true',
        help='Enable debug messages')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    args.output_dir = os.path.expanduser(args.output_dir)

    # turn off SSL certificate checking
    if args.insecure:
        yaxil.CHECK_CERTIFICATE = False

    # get xnat credentials    
    info = yaxil.auth(args.alias)

    # get the accession id for the supplied --label 
    try:
        aid = yaxil.accession(info, args.label, args.project)
    except yaxil.MultipleAccessionError:
        logger.critical('--label is too ambiguous, please specify --project')
        sys.exit(1)

    logger.debug('accession ID is %s' % aid)

    # only print scan information and quit
    if args.scan_only:
        scanonly(info, aid)
        sys.exit(0)

    # check if --scans was provided and query for scans
    if not args.scans:
        logger.critical('you must provide --scans')
        parser.print_help()
        sys.exit(1)

    if len(args.scans) == 1 and args.scans[0].strip().upper() == 'ALL':
        scans = ['ALL']
    else:
        query = {
            'scans': 'ID IN (%s)' % ','.join(args.scans)
        }
        scans = yaxil.scansearch(info, aid, query)
        scans = commons.flatten(scans.values())

    # download data
    yaxil.download(info, aid, scans, out_dir=args.output_dir, progress=1024**2, attempts=3)

def scanonly(credentials, aid):
    scans = yaxil.scans(credentials, fmt='json', accession=aid)['ResultSet']['Result']
    scans = [x for x in scans if x['xnat:mrscandata/id']]
    print('scan\tsequence\ttype\tnote')
    for scan in sorted(scans, key=lambda x: int(x['xnat:mrscandata/id'])):
        num = scan['xnat:mrscandata/id']
        series = scan['xnat:mrscandata/series_description']
        stype = scan['xnat:mrscandata/type']
        note = scan['xnat:mrscandata/note']
        print('%s\t%s\t%s\t%s' % (num, series, stype, note))

if __name__ == '__main__':
    main()
