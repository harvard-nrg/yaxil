import re
import os
import glob
import json
import string
import logging
import pydicom
import subprocess as sp
from pathlib import Path
import yaxil.commons as commons
from pydicom.errors import InvalidDicomError

logger = logging.getLogger(__name__)

# bids legal characters for sub, ses, and task
legal = re.compile('[^a-zA-Z0-9]')

def bids_from_config(yaxil_session, scans_metadata, config, out_base, in_mem=False):
    '''
    Create a BIDS output directory from configuration file
    '''
    # get session and subject labels from scan metadata
    _item = next(iter(scans_metadata))
    project,session,subject = _item['session_project'],_item['session_label'],_item['subject_label']
    session_id,subject_id = _item['session_id'],_item['subject_id']
    # check for dataset_description.json and create it if necessary
    check_dataset_description(out_base)
    # define bids and sourcedata base directories
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
    # put arguments in a struct for convenience
    args = commons.struct(
        xnat=yaxil_session,
        subject=subject,
        subject_id=subject_id,
        session=session,
        session_id=session_id,
        project=project,
        bids=bids_base,
        sourcedata=sourcedata_base,
        in_mem=in_mem
    )
    # process func, anat, and fmap
    refs = dict()
    refs.update(proc_func(config, args))
    refs.update(proc_anat(config, args))
    refs.update(proc_dwi(config, args))
    logger.debug(f'refs={refs}')
    proc_fmap(config, args, refs)

def check_dataset_description(bids_dir, bids_version='1.4.0', ds_type='raw'):
    if not os.path.exists(bids_dir):
        os.makedirs(bids_dir)
    ds_desc = os.path.join(bids_dir, 'dataset_description.json')
    if not os.path.exists(ds_desc):
        js = {
            'Name': 'Made by YAXIL',
            'BIDSVersion': bids_version,
            'DatasetType': ds_type
        }
        with open(ds_desc, 'w') as fo:
            fo.write(json.dumps(js))
    
def proc_func(config, args):
    '''
    Download functional data and convert to BIDS
    '''
    refs = dict()
    sub = legal.sub('', args.subject)
    ses = legal.sub('', args.session)
    for scan in iterconfig(config, 'func'):
        ref = scan.get('id', None)
        templ = 'sub-${sub}_ses-${ses}'
        if 'task' in scan:
            templ += '_task-${task}'
        if 'acquisition' in scan:
            templ += '_acq-${acquisition}'
        if 'direction' in scan:
            templ += '_dir-${direction}'
        if 'run' in scan:
            templ += '_run-${run}'
        templ += '_${modality}'
        templ = string.Template(templ)
        fbase = templ.safe_substitute(
            sub=sub,
            ses=ses,
            task=scan.get('task', None),
            acquisition=scan.get('acquisition', None),
            run=scan.get('run', None),
            direction=scan.get('direction', None),
            modality=scan.get('modality', None)
        )
        # download data to bids sourcedata directory
        sourcedata_dir = os.path.join(args.sourcedata, scan['type'])
        if not os.path.exists(sourcedata_dir):
            os.makedirs(sourcedata_dir)
        dicom_dir = os.path.join(sourcedata_dir, f'{fbase}.dicom')
        logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
        args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir, in_mem=args.in_mem)
        # convert to nifti
        fname = '{0}.nii.gz'.format(fbase)
        refs[ref] = os.path.join(f'ses-{ses}', scan['type'], fname)
        fullfile = os.path.join(args.bids, scan['type'], fname)
        logger.info('converting %s to %s', dicom_dir, fullfile)
        convert(dicom_dir, fullfile)
        # some applications need access to the number of stored bits
        bits_stored = get_bits_stored(dicom_dir)
        # add xnat source information and bits stored to json sidecar
        sidecar_file = os.path.join(args.bids, scan['type'], fbase + '.json')
        with open(sidecar_file) as fo:
            sidecarjs = json.load(fo, strict=False)
        if bits_stored:
            sidecarjs['BitsStored'] = bits_stored
        sidecarjs['DataSource'] = {
            'application/x-xnat': {
                'url': args.xnat.url,
                'project': args.project,
                'subject': args.subject,
                'subject_id': args.subject_id,
                'experiment': args.session,
                'experiment_id': args.session_id,
                'scan': scan['scan']
            }
        }
        # write out updated json sidecar
        commons.atomic_write(sidecar_file, json.dumps(sidecarjs, indent=2))
    return refs

def get_bits_stored(dicom_dir):
    '''
    Helper function to get Bits Stored (0028,0101) DICOM header
    '''
    for f in Path(dicom_dir).iterdir():
        try:
            ds = pydicom.dcmread(f)
            return ds.get('BitsStored', None)
        except InvalidDicomError as e:
            logger.debug(e)

def proc_anat(config, args):
    '''
    Download anatomical data and convert to BIDS
    '''
    refs = dict()
    sub = legal.sub('', args.subject)
    ses = legal.sub('', args.session)
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
            sub=sub,
            ses=ses,
            acquisition=scan.get('acquisition', None),
            run=scan.get('run', None),
            modality=scan.get('modality', None),
        )
        # download data to bids sourcedata directory
        sourcedata_dir = os.path.join(args.sourcedata, scan['type'])
        if not os.path.exists(sourcedata_dir):
            os.makedirs(sourcedata_dir)
        dicom_dir = os.path.join(sourcedata_dir, f'{fbase}.dicom')
        logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
        args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir, in_mem=args.in_mem)
        # convert to nifti (edge cases for T1w_vNav_setter)
        fname = '{0}.nii.gz'.format(fbase)
        refs[ref] = os.path.join(f'ses-{ses}', scan['type'], fname)
        fullfile = os.path.join(args.bids, scan['type'], fname)
        logger.info('converting %s to %s', dicom_dir, fullfile)
        modality = scan.get('modality', None)
        sidecar_files = list()
        if modality == 'T1vnav':
            fullfile = fullfile.replace('_T1vnav', '_split-%r_T1vnav')
            for f in glob.glob(os.path.join(dicom_dir, '*.dcm')):
                logger.debug('converting single file %s to %s', f, fullfile)
                convert(f, fullfile, single_file=True)
            ffbase = re.sub('.nii(.gz)?', '', fullfile)
            expr = ffbase.replace('%r', '*') + '.json'
            logger.debug('globbing for %s', expr)
            sidecar_files = glob.glob(expr)
        elif modality == 'T2vnav':
            fullfile = fullfile.replace('_T2vnav', '_split-%r_T2vnav')
            for f in glob.glob(os.path.join(dicom_dir, '*.dcm')):
                logger.debug('converting single file %s to %s', f, fullfile)
                convert(f, fullfile, single_file=True)
            ffbase = re.sub('.nii(.gz)?', '', fullfile)
            expr = ffbase.replace('%r', '*') + '.json'
            logger.debug('globbing for %s', expr)
            sidecar_files = glob.glob(expr)
        else:
            convert(dicom_dir, fullfile)
            sidecar_files = [
                os.path.join(args.bids, scan['type'], fbase + '.json')
            ]
        # add xnat source information to json sidecar files
        for sidecar_file in sidecar_files:
            logger.debug('adding provenance to %s', sidecar_file)
            with open(sidecar_file) as fo:
                sidecarjs = json.load(fo, strict=False)
            sidecarjs['DataSource'] = {
                'application/x-xnat': {
                    'url': args.xnat.url,
                    'project': args.project,
                    'subject': args.subject,
                    'subject_id': args.subject_id,
                    'experiment': args.session,
                    'experiment_id': args.session_id,
                    'scan': scan['scan']
                }
            }
            # write out updated json sidecar
            commons.atomic_write(sidecar_file, json.dumps(sidecarjs, indent=2))
    return refs

def proc_dwi(config, args):
    '''
    Download diffusion data and convert to BIDS
    '''
    refs = dict()
    sub = legal.sub('', args.subject)
    ses = legal.sub('', args.session)
    for scan in iterconfig(config, 'dwi'):
        ref = scan.get('id', None)
        templ = 'sub-${sub}_ses-${ses}'
        if 'acquisition' in scan:
            templ += '_acq-${acquisition}'
        if 'direction' in scan:
            templ += '_dir-${direction}'
        if 'run' in scan:
            templ += '_run-${run}'
        templ += '_${modality}'
        templ = string.Template(templ)
        fbase = templ.safe_substitute(
            sub=sub,
            ses=ses,
            acquisition=scan.get('acquisition', None),
            direction=scan.get('direction', None),
            run=scan.get('run', None),
            modality=scan.get('modality', None)
        )
        # download data to bids sourcedata directory
        sourcedata_dir = os.path.join(args.sourcedata, scan['type'])
        if not os.path.exists(sourcedata_dir):
            os.makedirs(sourcedata_dir)
        dicom_dir = os.path.join(sourcedata_dir, f'{fbase}.dicom')
        logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
        args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir, in_mem=args.in_mem)
        # convert to nifti
        fname = '{0}.nii.gz'.format(fbase)
        refs[ref] = os.path.join(f'ses-{ses}', scan['type'], fname)
        fullfile = os.path.join(args.bids, scan['type'], fname)
        logger.info('converting %s to %s', dicom_dir, fullfile)
        modality = scan.get('modality', None)
        convert(dicom_dir, fullfile)
        sidecar_file = os.path.join(args.bids, scan['type'], fbase + '.json')
        # add xnat source information to json sidecar files
        logger.debug('adding provenance to %s', sidecar_file)
        with open(sidecar_file) as fo:
            sidecarjs = json.load(fo, strict=False)
        sidecarjs['DataSource'] = {
            'application/x-xnat': {
                'url': args.xnat.url,
                'project': args.project,
                'subject': args.subject,
                'subject_id': args.subject_id,
                'experiment': args.session,
                'experiment_id': args.session_id,
                'scan': scan['scan']
            }
        }
        # write out updated json sidecar
        commons.atomic_write(sidecar_file, json.dumps(sidecarjs, indent=2))
    return refs

def proc_fmap(config, args, refs=None):
    fmap_refs = dict()
    sub = legal.sub('', args.subject)
    ses = legal.sub('', args.session)
    for scan in iterconfig(config, 'fmap'):
        ref = scan.get('id', None)
        templ = 'sub-${sub}_ses-${ses}'
        if 'acquisition' in scan:
            templ += '_acq-${acquisition}'
        if 'direction' in scan:
            templ += '_dir-${direction}'
        if 'run' in scan:
            templ += '_run-${run}'
        templ += '_${modality}'
        templ = string.Template(templ)
        fbase = templ.safe_substitute(
            sub=sub,
            ses=ses,
            acquisition=scan.get('acquisition', None),
            run=scan.get('run', None),
            direction=scan.get('direction', None),
            modality=scan.get('modality', None),
        )
        # download data to bids sourcedata directory
        sourcedata_dir = os.path.join(args.sourcedata, scan['type'])
        if not os.path.exists(sourcedata_dir):
            os.makedirs(sourcedata_dir)
        dicom_dir = os.path.join(sourcedata_dir, f'{fbase}.dicom')
        logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
        args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir, in_mem=args.in_mem)
        # convert to nifti
        fname = '{0}.nii.gz'.format(fbase)
        fmap_refs[ref] = os.path.join(f'ses-{ses}', scan['type'], fname)
        fullfile = os.path.join(args.bids, scan['type'], fname)
        logger.info('converting %s to %s', dicom_dir, fullfile)
        convert(dicom_dir, fullfile)
        # rename fieldmap images to BIDS file naming convention
        if scan['type'] == 'fmap':
            if scan.get('modality', None) == 'magnitude':
                rename_fmapm(args.bids, fbase)
            elif scan.get('modality', None) == 'phase':
                rename_fmapp(args.bids, fbase)
        # add xnat source information to json sidecar
        sidecar_file = os.path.join(args.bids, scan['type'], fbase + '.json')
        with open(sidecar_file, 'r') as fo:
            sidecarjs = json.load(fo, strict=False)
        sidecarjs['DataSource'] = {
            'application/x-xnat': {
                'url': args.xnat.url,
                'project': args.project,
                'subject': args.subject,
                'subject_id': args.subject_id,
                'experiment': args.session,
                'experiment_id': args.session_id,
                'scan': scan['scan']
            }
        }
        # insert intended-for into json sidecar
        if 'intended for' in scan and refs:
            for intended in scan['intended for']:
                if intended in refs:
                    logger.info('adding IntendedFor %s to %s', refs[intended], sidecar_file)
                    if 'IntendedFor' not in sidecarjs:
                        sidecarjs['IntendedFor'] = list()
                    if refs[intended] not in sidecarjs['IntendedFor']:
                        sidecarjs['IntendedFor'].append(refs[intended])
            logger.info('writing file %s', sidecar_file)
        # write out updated json sidecar
        commons.atomic_write(sidecar_file, json.dumps(sidecarjs, indent=2))
    return fmap_refs

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

def convert(input, output, single_file=False):
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
        'dcm2niix'
    ]
    if single_file:
        cmd.extend([
            '-s', 'y'
        ])
    cmd.extend([
        '-b', 'y',
        '-z', 'y',
        '-f', basename,
        '-o', dirname,
        input
    ])
    logger.debug(cmd)
    sp.check_output(cmd)
