import re
import os
import sys
import json
import string
import logging
import pydicom
from glob import glob
import subprocess as sp
from pathlib import Path
import yaxil.commons as commons
from collections import defaultdict
from pydicom.errors import InvalidDicomError

logger = logging.getLogger(__name__)

# bids legal characters for sub, ses, and task
legal = re.compile(r'[^a-zA-Z0-9]')

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
        out_base=out_base,
        sourcedata=sourcedata_base,
        in_mem=in_mem
    )
    # process func, anat, and fmap
    refs = dict()
    refs.update(proc_func(config, args))    
    refs.update(proc_anat(config, args))
    refs.update(proc_dwi(config, args))
    logger.info('references')
    logger.info(json.dumps(refs, indent=2))
    proc_fmap(config, args, refs)

def check_dataset_description(bids_dir, bids_version='1.4.0', ds_type='raw'):
    os.makedirs(bids_dir, exist_ok=True)
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
    for scan in iterconfig(config, 'func'):
        ref = scan.get('id', None)
        files = _proc_func(scan, config, args)
        refs[ref] = files
    return refs

def _restem(source, newstem):
    parent = source.parent
    suffix = ''.join(source.suffixes)
    oldstem = re.sub('.nii', '', source.stem)
    source_sidecar = Path(parent, f'{oldstem}.json')
    destination = Path(parent, f'{newstem}{suffix}')
    destination_sidecar = Path(parent, f'{newstem}.json')
    logger.info(f'renaming {source} to {destination}')
    logger.info(f'renaming {source_sidecar} to {destination_sidecar}')
    if destination.exists():
        raise FileExistsError(destination)
    source.rename(destination)
    if destination_sidecar.exists():
        raise FileExistsError(destination_sidecar)
    source_sidecar.rename(destination_sidecar)
    return destination

def _proc_func(scan, config, args):
    files = list()
    sub = legal.sub('', args.subject)
    ses = legal.sub('', args.session)
    templ = 'sub-${sub}_ses-${ses}'
    if 'task' in scan:
        templ += '_task-${task}'
    if 'acquisition' in scan:
        templ += '_acq-${acquisition}'
    if 'direction' in scan:
        templ += '_dir-${direction}'
    if 'run' in scan:
        templ += '_run-${run}'
    templ += '_echo-%e_${modality}'
    templ = string.Template(templ)
    stem = templ.safe_substitute(
        sub=sub,
        ses=ses,
        task=scan.get('task', None),
        acquisition=scan.get('acquisition', None),
        run=scan.get('run', None),
        direction=scan.get('direction', None),
        modality=scan.get('modality', None)
    )
    stem_noecho = re.sub('_echo-%e', '', stem)
    # download data to bids sourcedata directory
    sourcedata_dir = Path(args.sourcedata, scan['type'])
    sourcedata_dir.mkdir(parents=True, exist_ok=True)
    dicom_dir = Path(sourcedata_dir, f'{stem_noecho}.dicom')
    scanid = scan['scan']
    logger.info(f'downloading session={args.session}, scan={scanid}, loc={dicom_dir}')
    args.xnat.download(
        args.session,
        [
            scanid
        ],
        out_dir=dicom_dir,
        attempts=3,
        in_mem=args.in_mem
    )
    suffix = '.nii.gz'
    # convert dicoms to nifti
    scandir = Path(args.bids, scan['type'])
    fname = f'{stem}{suffix}'
    fullfile = Path(scandir, fname)
    logger.info(f'converting {dicom_dir} to {fullfile}')
    convert(dicom_dir, fullfile)
    # remove echo entity if the current scan is a single echo
    wildcard = re.sub('_echo-%e', '_echo-*', fname)
    logger.info(f'running glob {wildcard} on {scandir} for niftis')
    niftis = list(scandir.glob(wildcard))
    if len(niftis) == 1:
        niftis = [
            _restem(niftis.pop(), stem_noecho)
        ]
        stem = stem_noecho
    # compile list of files
    for nifti in niftis:
        relpath = Path(f'ses-{ses}', scan['type'], nifti.name)
        files.append(str(relpath))
    # some applications need access to the number of stored bits
    bits_stored = get_bits_stored(dicom_dir)
    # add xnat source information and bits stored to json sidecar
    wildcard = re.sub('_echo-%e', '_echo-*', f'{stem}.json')
    logger.info(f'running glob {wildcard} on {scandir} for sidecars')
    for sidecar in scandir.glob(wildcard):
        with open(sidecar) as fo:
            js = json.load(fo, strict=False)
        if bits_stored:
            js['BitsStored'] = bits_stored
        js['DataSource'] = {
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
        commons.atomic_write(
            sidecar,
            json.dumps(
                js,
                indent=2
            )
        )
    return files

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
    for scan in iterconfig(config, 'anat'):
        ref = scan.get('id', None)
        files = _proc_anat(scan, config, args)
        refs[ref] = files
    return refs

def _proc_anat(scan, config, args):
    refs = list()
    sub = legal.sub('', args.subject)
    ses = legal.sub('', args.session)
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
    os.makedirs(sourcedata_dir, exist_ok=True)
    dicom_dir = os.path.join(sourcedata_dir, f'{fbase}.dicom')
    logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
    args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir, attempts=3, in_mem=args.in_mem)
    # convert to nifti (edge cases for T1w_vNav_setter)
    fname = '{0}.nii.gz'.format(fbase)
    refs.append(os.path.join(f'ses-{ses}', scan['type'], fname))
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
    for scan in iterconfig(config, 'dwi'):
        ref = scan.get('id', None)
        files = _proc_dwi(scan, config, args)
        refs[ref] = files
    return refs

def _proc_dwi(scan, config, args):
    refs = list() 
    sub = legal.sub('', args.subject)
    ses = legal.sub('', args.session)
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
    os.makedirs(sourcedata_dir, exist_ok=True)
    dicom_dir = os.path.join(sourcedata_dir, f'{fbase}.dicom')
    logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
    args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir, attempts=3, in_mem=args.in_mem)
    # convert to nifti
    fname = '{0}.nii.gz'.format(fbase)
    refs.append(os.path.join(f'ses-{ses}', scan['type'], fname))
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
    for scan in iterconfig(config, 'fmap'):
        ref = scan.get('id', None)
        files = _proc_fmap(scan, config, args, refs)
        refs[ref] = files
    return refs

def _proc_fmap(scan, config, args, refs=None):
    sub = legal.sub('', args.subject)
    ses = legal.sub('', args.session)
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
    os.makedirs(sourcedata_dir, exist_ok=True)
    dicom_dir = os.path.join(sourcedata_dir, f'{fbase}.dicom')
    logger.info('downloading session=%s, scan=%s, loc=%s', args.session, scan['scan'], dicom_dir)
    args.xnat.download(args.session, [scan['scan']], out_dir=dicom_dir, attempts=3, in_mem=args.in_mem)
    # convert to nifti
    fname = '{0}.nii.gz'.format(fbase)
    fullfile = os.path.join(args.bids, scan['type'], fname)
    logger.info('converting %s to %s', dicom_dir, fullfile)
    convert(dicom_dir, fullfile)
    # rename fieldmap images to BIDS file naming convention
    modality = scan.get('modality', None)
    if scan['type'] == 'fmap':
        if modality == 'magnitude':
            logger.debug('renaming fmap magnitude files')
            files = _fmap_magnitude(args.bids, fbase)
        elif modality == 'phasediff':
            logger.debug('renaming phasediff file')
            files = _fmap_phasediff(args.bids, fbase)
        elif modality == 'epi':
            files = _fmap_epi(args.bids, fbase)
        else:
            raise FmapError(f'unexpected fmap modality {modality}')
    # add xnat source information to json sidecar
    for sidecar_file in files['json']:
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
        # insert intended-for into json sidecar
        if 'intended for' in scan and refs:
            for intended in scan['intended for']:
                if intended in refs:
                    infors = refs[intended]
                    logger.info(f'adding IntendedFor {infors} to {sidecar_file}')
                    if 'IntendedFor' not in sidecarjs:
                        sidecarjs['IntendedFor'] = list()
                    if infors not in sidecarjs['IntendedFor']:
                        sidecarjs['IntendedFor'].extend(infors)
        # write out updated json sidecar
        logger.info(f'writing out new file {sidecar_file}')
        commons.atomic_write(
            sidecar_file,
            json.dumps(
                sidecarjs,
                indent=2
            )
        )
 
def _fmap_epi(bids_base, basename):
    '''
    Rename to BIDS and return api fieldmap files
    '''
    result = defaultdict(list)
    for ext in ['nii.gz', 'json']:
        source = Path(
            bids_base,
            'fmap',
            f'{basename}.{ext}'
        )
        if not source.exists():
            continue
        result[ext].append(source)
    return result

def _fmap_magnitude(bids_base, basename):
    '''
    Rename to BIDS and return magnitude fieldmap files
    '''
    result = defaultdict(list)
    for ext in ['nii.gz', 'json']:
        for echo in [1, 2]:
            source = Path(
                bids_base,
                'fmap',
                f'{basename}_e{echo}.{ext}'
            )
            if not source.exists():
                continue
            fname = source.name.replace(
                f'magnitude_e{echo}',
                f'magnitude{echo}'
            )
            destination = Path(source.parent, fname)
            logger.debug(f'renaming {source} to {destination}')
            source.rename(destination)
            result[ext].append(destination)
    return result
    
def _fmap_phasediff(bids_base, basename):
    '''
    Rename to BIDS and return phasediff fieldmap files
    '''
    result = defaultdict(list)
    for ext in ['nii.gz', 'json']:
        path = Path(bids_base, 'fmap')
        expr = f'{basename}_e*_ph.{ext}'
        files = list(path.glob(expr))
        numfiles = len(files)
        if numfiles != 1:
            raise FmapError(f'found {numfiles} fmap files from {expr}')
        source = files.pop()
        fname = re.sub(
            f'phasediff_e\d+_ph',
            f'phasediff',
            source.name
        )
        destination = Path(source.parent, fname)
        logger.debug(f'renaming {source} to {destination}')
        source.rename(destination)
        result[ext].append(destination)
    return result

class FmapError(Exception):
    pass

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

def convert(input, output, single_file=False):
    '''
    Run dcm2niix on input file
    '''
    dirname = os.path.dirname(output)
    os.makedirs(dirname, exist_ok=True)
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

