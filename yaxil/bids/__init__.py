import re
import os
import json
import string
import logging
import subprocess as sp
import yaxil.commons as commons

logger = logging.getLogger(__name__)

# bids legal characters for sub, ses, and task
legal = re.compile('[^a-zA-Z0-9]')

def bids_from_config(sess, scans_metadata, config, out_base):
    '''
    Create a BIDS output directory from configuration file
    '''
    # get session and subject labels from scan metadata
    _item = next(iter(scans_metadata))
    session,subject = _item['session_label'],_item['subject_label']
    # bids and sourcedata base directories
    sourcedata_base = os.path.join(
        out_base,
        'sourcedata',
        'sub-{0}'.format(legal.sub('', subject)),
        'ses-{0}'.format(legal.sub('', session))
    )
    bids_base = os.path.join(
        out_base,
        'sub-{0}'.format(legal.sub('', subject)),
        'ses-{0}'.format(legal.sub('', session))
    )
    # put arguments in a struct
    args = commons.struct(
        xnat=sess,
        subject=subject,
        session=session,
        bids=bids_base,
        sourcedata=sourcedata_base
    )
    # process func, anat, and fmap
    func_refs = proc_func(config, args)
    anat_refs = proc_anat(config, args)
    fmap_refs = proc_fmap(config, args, func_refs)

def proc_func(config, args):
    '''
    Download functional data and convert to BIDS
    '''
    refs = dict()
    for scan in iterconfig(config, 'func'):
        ref = scan.get('id', None)
        templ = 'sub-${sub}_ses-${ses}_task-${task}'
        if 'acquisition' in scan:
            templ += '_acq-${acquisition}'
        if 'run' in scan:
            templ += '_run-${run}'
        if 'direction' in scan:
            templ += '_dir-${direction}'
        templ += '_${modality}'
        templ = string.Template(templ)
        fbase = templ.safe_substitute(
            sub=legal.sub('', args.subject),
            ses=legal.sub('', args.session),
            task=scan.get('task', None),
            acquisition=scan.get('acquisition', None),
            run=scan.get('run', None),
            direction=scan.get('direction', None),
            modality=scan.get('modality', None),
        )
        # download data to bids sourcedata directory
        sourcedata_dir = os.path.join(args.sourcedata, scan['type'])
        if not os.path.exists(sourcedata_dir):
            os.makedirs(sourcedata_dir)
        dicom_dir = os.path.join(sourcedata_dir, '{0}.dicom'.format(fbase))
        logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
        args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir)
        # convert to nifti
        fname = '{0}.nii.gz'.format(fbase)
        refs[ref] = os.path.join(scan['type'], fname)
        fullfile = os.path.join(args.bids, scan['type'], fname)
        logger.info('converting %s to %s', dicom_dir, fullfile)
        convert(dicom_dir, fullfile)
    return refs

def proc_anat(config, args):
    '''
    Download anatomical data and convert to BIDS
    '''
    refs = dict()
    for scan in iterconfig(config, 'anat'):
        ref = scan.get('id', None)
        templ = 'sub-${sub}_ses-${ses}'
        if 'acquisition' in scan:
            templ += '_acq-${acquisition}'
        if 'run' in scan:
            templ += '_run-${run}'
        templ += '_${modality}'
        templ = string.Template(templ)
        fbase = templ.safe_substitute(
            sub=legal.sub('', args.subject),
            ses=legal.sub('', args.session),
            acquisition=scan.get('acquisition', None),
            run=scan.get('run', None),
            modality=scan.get('modality', None),
        )
        # download data to bids sourcedata directory
        sourcedata_dir = os.path.join(args.sourcedata, scan['type'])
        if not os.path.exists(sourcedata_dir):
            os.makedirs(sourcedata_dir)
        dicom_dir = os.path.join(sourcedata_dir, '{0}.dicom'.format(fbase))
        logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
        args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir)
        # convert to nifti
        fname = '{0}.nii.gz'.format(fbase)
        refs[ref] = os.path.join(scan['type'], fname)
        fullfile = os.path.join(args.bids, scan['type'], fname)
        logger.info('converting %s to %s', dicom_dir, fullfile)
        convert(dicom_dir, fullfile)
    return refs

def proc_fmap(config, args, func_refs=None):
    refs = dict()
    for scan in iterconfig(config, 'fmap'):
        ref = scan.get('id', None)
        templ = 'sub-${sub}_ses-${ses}'
        if 'acquisition' in scan:
            templ += '_acq-${acquisition}'
        if 'run' in scan:
            templ += '_run-${run}'
        if 'direction' in scan:
            templ += '_dir-${direction}'
        templ += '_${modality}'
        templ = string.Template(templ)
        fbase = templ.safe_substitute(
            sub=legal.sub('', args.subject),
            ses=legal.sub('', args.session),
            acquisition=scan.get('acquisition', None),
            run=scan.get('run', None),
            direction=scan.get('direction', None),
            modality=scan.get('modality', None),
        )
        # download data to bids sourcedata directory
        sourcedata_dir = os.path.join(args.sourcedata, scan['type'])
        if not os.path.exists(sourcedata_dir):
            os.makedirs(sourcedata_dir)
        dicom_dir = os.path.join(sourcedata_dir, '{0}.dicom'.format(fbase))
        logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
        args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir)
        # convert to nifti
        fname = '{0}.nii.gz'.format(fbase)
        refs[ref] = os.path.join(scan['type'], fname)
        fullfile = os.path.join(args.bids, scan['type'], fname)
        logger.info('converting %s to %s', dicom_dir, fullfile)
        convert(dicom_dir, fullfile)
        # rename fieldmap images to BIDS file naming convention
        if scan['type'] == 'fmap':
            if scan.get('modality', None) == 'magnitude':
                rename_fmapm(args.bids, fbase)
            elif scan.get('modality', None) == 'phase':
                rename_fmapp(args.bids, fbase)
        # get the json sidecar
        sidecar_file = os.path.join(args.bids, scan['type'], fbase + '.json')
        # insert intended-for into JSON sidecar
        if 'intended for' in scan and func_refs:
            with open(sidecar_file, 'r') as fo:
                sidecarjs = json.load(fo)
            for intended in scan['intended for']:
                if intended in func_refs:
                    logger.info('adding IntendedFor %s to %s', func_refs[intended], sidecar_file)
                    if 'IntendedFor' not in sidecarjs:
                        sidecarjs['IntendedFor'] = list()
                    if func_refs[intended] not in sidecarjs['IntendedFor']:
                        sidecarjs['IntendedFor'].append(func_refs[intended])
            # if there is only one IntendedFor entry, don't store in a list
            #if 'IntendedFor' in sidecarjs and len(sidecarjs['IntendedFor']) == 1:
            #    sidecarjs['IntendedFor'] = sidecarjs['IntendedFor'].pop()
            logger.info('writing file %s', sidecar_file)
            commons.atomic_write(sidecar_file, json.dumps(sidecarjs, indent=2))
    return refs

def iterconfig(config, scan_type):
    '''
    Iterate over BIDS configuration file
    '''
    if scan_type in config:
        for modality,scans in iter(config[scan_type].items()):
            for scan in scans:
                scan.update({
                    'type': scan_type,
                    'modality': modality
                })
                yield scan

def rename_fmapm(bids_base, basename):
    '''
    Rename magnitude fieldmap file to BIDS specification
    '''
    files = dict()
    for ext in ['nii.gz', 'json']:
        for echo in [1, 2]:
            fname = '{0}_e{1}.{2}'.format(basename, echo, ext)
            src = os.path.join(bids_base, 'fmap', fname)
            if os.path.exists(src):
                dst = src.replace(
                    'magnitude_e{0}'.format(echo),
                    'magnitude{0}'.format(echo)
                )
                logger.debug('renaming %s to %s', src, dst)
                os.rename(src, dst)
                files[ext] = dst
    return files

def rename_fmapp(bids_base, basename):
    '''
    Rename phase fieldmap file to BIDS specification
    '''
    files = dict()
    for ext in ['nii.gz', 'json']:
        fname = '{0}_e2_ph.{1}'.format(basename, ext)
        src = os.path.join(bids_base, 'fmap', fname)
        if os.path.exists(src):
            dst = src.replace(
                'phase_e2_ph',
                'phase'
            )
            logger.debug('renaming %s to %s', src, dst)
            os.rename(src, dst)
            files[ext] = dst
    return files

def convert(input, output):
    '''
    Run dcm2niix on input file
    '''
    dirname = os.path.dirname(output)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    basename = os.path.basename(output)
    basename = re.sub('.nii(.gz)?', '', basename)
    dcm2niix = commons.which('dcm2niix')
    cmd = [
        'dcm2niix',
        '-s', 'y',
        '-b', 'y',
        '-z', 'y',
        '-f', basename,
        '-o', dirname,
        input
    ]
    logger.debug(cmd)
    sp.check_output(cmd)
