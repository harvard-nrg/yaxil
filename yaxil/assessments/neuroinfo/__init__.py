import yaxil
from contextlib import contextmanager
from yaxil.assessments.neuroinfo.session import Session

@contextmanager
def session(auth):
    '''
    Create a session context to avoid explicitly passing authentication to
    every function.

    Example:
        >>> import json
        >>> import yaxil.assessments.neuroinfo as neuroinfo
        >>> auth = yaxil.auth('doctest')
        >>> with neuroinfo.session(auth) as ses:
        ...   for qc in ses.anatqc('TestSession01'):
        ...     print(json.dumps(qc, indent=2))
        {
          "id": "TestSession01_ANAT_30_AQC",
          ...
        }

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :returns: YAXIL session object
    :rtype: :mod:`yaxil.assessments.neuroinfo.session.Session`
    '''
    yield Session(auth)

def boldqc(auth, label=None, scan_ids=None, project=None, aid=None):
    '''
    Get BOLDQC data as a sequence of dictionaries.

    Example:
        >>> import json
        >>> import yaxil.assessments.neuroinfo as neuroinfo
        >>> auth = yaxil.auth('doctest')
        >>> for qc in neuroinfo.boldqc(auth, 'TestSession01'):
        ...   print(json.dumps(qc, indent=2))
        {
          "id": "TestSession01_BOLD_17_EQC",
          ...
        }

    :param auth: XNAT authentication object
    :type auth: :mod:`yaxil.XnatAuth`
    :param label: XNAT MR Session label
    :type label: str
    :param scan_ids: Scan numbers to include
    :type scan_ids: list
    :param project: XNAT MR Session project
    :type project: str
    :param aid: XNAT MR Session Accession ID
    :type aid: str
    :returns: Generator of BOLDQC data dictionaries
    :rtype: :mod:`dict`
    '''
    if not aid:
        if not label:
            raise ValueError('you must provide label or aid')
        aid = yaxil.accession(auth, label, project)
    experiment_details = yaxil.__experiment_details(auth, aid)
    path = '/data/experiments'
    params = {
        'xsiType': 'neuroinfo:boldqc',
        'columns': ','.join(boldqc.columns.keys())
    }
    if project:
        params['project'] = project
    params['xnat:mrSessionData/ID'] = aid
    _,result = yaxil._get(auth, path, 'json', autobox=True, params=params)
    for result in result['ResultSet']['Result']:
        if scan_ids == None or result['neuroinfo:boldqc/bold_scan_id'] in scan_ids:
            data = dict()
            for k,v in iter(boldqc.columns.items()):
                data[v] = result[k]
            files = __files(auth, result['neuroinfo:boldqc/id'])
            data.update(experiment_details)
            data['files'] = files
            yield data
boldqc.columns = {
    'neuroinfo:boldqc/id': 'ID',
    'neuroinfo:boldqc/id': 'id',
    'neuroinfo:boldqc/date': 'date',
    'neuroinfo:boldqc/time': 'time',
    'neuroinfo:boldqc/imagesession_id': 'session_id',
    'neuroinfo:boldqc/bold_scan_id': 'bold_scan_id',
    'neuroinfo:boldqc/session_label': 'session_label',
    'neuroinfo:boldqc/size': 'size',
    'neuroinfo:boldqc/n_vols': 'n_vols',
    'neuroinfo:boldqc/skip': 'skip',
    'neuroinfo:boldqc/qc_n_tps': 'qc_n_tps',
    'neuroinfo:boldqc/qc_thresh': 'qc_thresh',
    'neuroinfo:boldqc/qc_nvox': 'qc_nvox',
    'neuroinfo:boldqc/qc_mean': 'qc_mean',
    'neuroinfo:boldqc/qc_max': 'qc_max',
    'neuroinfo:boldqc/qc_min': 'qc_min',
    'neuroinfo:boldqc/qc_stdev': 'qc_stdev',
    'neuroinfo:boldqc/qc_ssnr': 'qc_ssnr',
    'neuroinfo:boldqc/qc_vsnr': 'qc_vsnr',
    'neuroinfo:boldqc/qc_slope': 'qc_slope',
    'neuroinfo:boldqc/mot_n_tps': 'mot_n_tps',
    'neuroinfo:boldqc/mot_rel_x_mean': 'mot_rel_x_mean',
    'neuroinfo:boldqc/mot_rel_x_sd': 'mot_rel_x_sd',
    'neuroinfo:boldqc/mot_rel_x_max': 'mot_rel_x_max',
    'neuroinfo:boldqc/mot_rel_x_1mm': 'mot_rel_x_1mm',
    'neuroinfo:boldqc/mot_rel_x_5mm': 'mot_rel_x_5mm',
    'neuroinfo:boldqc/mot_rel_y_mean': 'mot_rel_y_mean',
    'neuroinfo:boldqc/mot_rel_y_sd': 'mot_rel_y_sd',
    'neuroinfo:boldqc/mot_rel_y_max': 'mot_rel_y_max',
    'neuroinfo:boldqc/mot_rel_y_1mm': 'mot_rel_y_1mm',
    'neuroinfo:boldqc/mot_rel_y_5mm': 'mot_rel_y_5mm',
    'neuroinfo:boldqc/mot_rel_z_mean': 'mot_rel_z_mean',
    'neuroinfo:boldqc/mot_rel_z_sd': 'mot_rel_z_sd',
    'neuroinfo:boldqc/mot_rel_z_max': 'mot_rel_z_max',
    'neuroinfo:boldqc/mot_rel_z_1mm': 'mot_rel_z_1mm',
    'neuroinfo:boldqc/mot_rel_z_5mm': 'mot_rel_z_5mm',
    'neuroinfo:boldqc/mot_rel_xyz_mean': 'mot_rel_xyz_mean',
    'neuroinfo:boldqc/mot_rel_xyz_sd': 'mot_rel_xyz_sd',
    'neuroinfo:boldqc/mot_rel_xyz_max': 'mot_rel_xyz_max',
    'neuroinfo:boldqc/mot_rel_xyz_1mm': 'mot_rel_xyz_1mm',
    'neuroinfo:boldqc/mot_rel_xyz_5mm': 'mot_rel_xyz_5mm',
    'neuroinfo:boldqc/rot_rel_x_mean': 'rot_rel_x_mean',
    'neuroinfo:boldqc/rot_rel_x_sd': 'rot_rel_x_sd',
    'neuroinfo:boldqc/rot_rel_x_max': 'rot_rel_x_max',
    'neuroinfo:boldqc/rot_rel_y_mean': 'rot_rel_y_mean',
    'neuroinfo:boldqc/rot_rel_y_sd': 'rot_rel_y_sd',
    'neuroinfo:boldqc/rot_rel_y_max': 'rot_rel_y_max',
    'neuroinfo:boldqc/rot_rel_z_mean': 'rot_rel_z_mean',
    'neuroinfo:boldqc/rot_rel_z_sd': 'rot_rel_z_sd',
    'neuroinfo:boldqc/rot_rel_z_max': 'rot_rel_z_max',
    'neuroinfo:boldqc/mot_abs_x_mean': 'mot_abs_x_mean',
    'neuroinfo:boldqc/mot_abs_x_sd': 'mot_abs_x_sd',
    'neuroinfo:boldqc/mot_abs_x_max': 'mot_abs_x_max',
    'neuroinfo:boldqc/mot_abs_y_mean': 'mot_abs_y_mean',
    'neuroinfo:boldqc/mot_abs_y_sd': 'mot_abs_y_sd',
    'neuroinfo:boldqc/mot_abs_y_max': 'mot_abs_y_max',
    'neuroinfo:boldqc/mot_abs_z_mean': 'mot_abs_z_mean',
    'neuroinfo:boldqc/mot_abs_z_sd': 'mot_abs_z_sd',
    'neuroinfo:boldqc/mot_abs_z_max': 'mot_abs_z_max',
    'neuroinfo:boldqc/mot_abs_xyz_mean': 'mot_abs_xyz_mean',
    'neuroinfo:boldqc/mot_abs_xyz_sd': 'mot_abs_xyz_sd',
    'neuroinfo:boldqc/mot_abs_xyz_max': 'mot_abs_xyz_max',
    'neuroinfo:boldqc/rot_abs_x_mean': 'rot_abs_x_mean',
    'neuroinfo:boldqc/rot_abs_x_sd': 'rot_abs_x_sd',
    'neuroinfo:boldqc/rot_abs_x_max': 'rot_abs_x_max',
    'neuroinfo:boldqc/rot_abs_y_mean': 'rot_abs_y_mean',
    'neuroinfo:boldqc/rot_abs_y_sd': 'rot_abs_y_sd',
    'neuroinfo:boldqc/rot_abs_y_max': 'rot_abs_y_max',
    'neuroinfo:boldqc/rot_abs_z_mean': 'rot_abs_z_mean',
    'neuroinfo:boldqc/rot_abs_z_sd': 'rot_abs_z_sd',
    'neuroinfo:boldqc/rot_abs_z_max': 'rot_abs_z_max',
    'neuroinfo:boldqc/manual/motion': 'manual_motion',
    'neuroinfo:boldqc/manual/cover': 'manual_cover',
    'neuroinfo:boldqc/manual/inhom': 'manual_inhom',
    'neuroinfo:boldqc/manual/ghost_brain': 'manual_ghost_brain',
    'neuroinfo:boldqc/manual/ghost_out': 'manual_ghost_out',
    'neuroinfo:boldqc/manual/spike': 'manual_spike',
    'neuroinfo:boldqc/manual/overall': 'manual_overall'
}

def t2qc(auth, label, scan_ids=None, project=None, aid=None):
    '''
    Get T2QC data as a sequence of dictionaries.

    Example:
        >>> import json
        >>> import yaxil.assessments.neuroinfo as neuroinfo
        >>> auth = yaxil.auth('doctest')
        >>> for qc in neuroinfo.t2qc(auth, 'TestSession01'):
        ...   print(json.dumps(qc, indent=2))
        {
          "id": "TestSession01_T2w_30_T2QC",
          ...
        }

    :param auth: XNAT authentication object
    :type auth: :mod:`yaxil.XnatAuth`
    :param label: XNAT MR Session label
    :type label: str
    :param scan_ids: Scan numbers to include
    :type scan_ids: list
    :param project: XNAT MR Session project
    :type project: str
    :param aid: XNAT MR Session Accession ID
    :type aid: str
    :returns: Generator of T2QC data dictionaries
    :rtype: :mod:`dict`
    '''
    if not aid:
        aid = yaxil.accession(auth, label, project)
    experiment_details = yaxil.__experiment_details(auth, aid)
    path = '/data/experiments'
    params = {
        'xsiType': 'neuroinfo:t2qc',
        'columns': ','.join(t2qc.columns.keys())
    }
    if project:
        params['project'] = project
    params['xnat:mrSessionData/ID'] = aid
    _,result = yaxil._get(auth, path, 'json', autobox=True, params=params)
    for result in result['ResultSet']['Result']:
        if scan_ids == None or result['neuroinfo:t2qc/t2w_scan_id'] in scan_ids:
            data = dict()
            for k,v in iter(t2qc.columns.items()):
                data[v] = result[k]
            files = __files(auth, result['neuroinfo:t2qc/id'])
            data.update(experiment_details)
            data['files'] = files
            yield data
t2qc.columns = {
    'neuroinfo:t2qc/id': 'ID',
    'neuroinfo:t2qc/id': 'id',
    'neuroinfo:t2qc/date': 'date',
    'neuroinfo:t2qc/time': 'time',
    'neuroinfo:t2qc/imagesession_id': 'session_id',
    'neuroinfo:t2qc/t2w_scan_id': 't2w_scan_id',
    'neuroinfo:t2qc/vnav_scan_id': 'vnav_scan_id',
    'neuroinfo:t2qc/session_label': 'session_label',
    'neuroinfo:t2qc/mriqc/cjv': 'mriqc_cjv',
    'neuroinfo:t2qc/mriqc/cnr': 'mriqc_cnr',
    'neuroinfo:t2qc/mriqc/efc': 'mriqc_efc',
    'neuroinfo:t2qc/mriqc/fber': 'mriqc_fber',
    'neuroinfo:t2qc/mriqc/fwhm_avg': 'mriqc_fwhm_avg',
    'neuroinfo:t2qc/mriqc/fwhm_x': 'mriqc_fwhm_x',
    'neuroinfo:t2qc/mriqc/fwhm_y': 'mriqc_fwhm_y',
    'neuroinfo:t2qc/mriqc/fwhm_z': 'mriqc_fwhm_z',
    'neuroinfo:t2qc/mriqc/icvs_csf': 'mriqc_icvs_csf',
    'neuroinfo:t2qc/mriqc/icvs_gm': 'mriqc_icvs_gm',
    'neuroinfo:t2qc/mriqc/icvs_wm': 'mriqc_icvs_wm',
    'neuroinfo:t2qc/mriqc/inu_med': 'mriqc_inu_med',
    'neuroinfo:t2qc/mriqc/inu_range': 'mriqc_inu_range',
    'neuroinfo:t2qc/mriqc/qi_1': 'mriqc_qi_1',
    'neuroinfo:t2qc/mriqc/qi_2': 'mriqc_qi_2',
    'neuroinfo:t2qc/mriqc/rpve_csf': 'mriqc_rpve_csf',
    'neuroinfo:t2qc/mriqc/rpve_gm': 'mriqc_rpve_gm',
    'neuroinfo:t2qc/mriqc/rpve_wm': 'mriqc_rpve_wm',
    'neuroinfo:t2qc/mriqc/size_x': 'mriqc_size_x',
    'neuroinfo:t2qc/mriqc/size_y': 'mriqc_size_y',
    'neuroinfo:t2qc/mriqc/size_z': 'mriqc_size_z',
    'neuroinfo:t2qc/mriqc/snr_csf': 'mriqc_snr_csf',
    'neuroinfo:t2qc/mriqc/snr_gm': 'mriqc_snr_gm',
    'neuroinfo:t2qc/mriqc/snr_total': 'mriqc_snr_total',
    'neuroinfo:t2qc/mriqc/snr_wm': 'mriqc_snr_wm',
    'neuroinfo:t2qc/mriqc/snrd_csf': 'mriqc_snrd_csf',
    'neuroinfo:t2qc/mriqc/snrd_gm': 'mriqc_snrd_gm',
    'neuroinfo:t2qc/mriqc/snrd_total': 'mriqc_snrd_total',
    'neuroinfo:t2qc/mriqc/snrd_wm': 'mriqc_snrd_wm',
    'neuroinfo:t2qc/mriqc/spacing_x': 'mriqc_spacing_x',
    'neuroinfo:t2qc/mriqc/spacing_y': 'mriqc_spacing_y',
    'neuroinfo:t2qc/mriqc/spacing_z': 'mriqc_spacing_z',
    'neuroinfo:t2qc/mriqc/summary_bg_k': 'mriqc_summary_bg_k',
    'neuroinfo:t2qc/mriqc/summary_bg_mad': 'mriqc_summary_bg_mad',
    'neuroinfo:t2qc/mriqc/summary_bg_mean': 'mriqc_summary_bg_mean',
    'neuroinfo:t2qc/mriqc/summary_bg_median': 'mriqc_summary_bg_median',
    'neuroinfo:t2qc/mriqc/summary_bg_n': 'mriqc_summary_bg_n',
    'neuroinfo:t2qc/mriqc/summary_bg_p05': 'mriqc_summary_bg_p05',
    'neuroinfo:t2qc/mriqc/summary_bg_p95': 'mriqc_summary_bg_p95',
    'neuroinfo:t2qc/mriqc/summary_bg_stdv': 'mriqc_summary_bg_stdv',
    'neuroinfo:t2qc/mriqc/summary_csf_k': 'mriqc_summary_csf_k',
    'neuroinfo:t2qc/mriqc/summary_csf_mad': 'mriqc_summary_csf_mad',
    'neuroinfo:t2qc/mriqc/summary_csf_mean': 'mriqc_summary_csf_mean',
    'neuroinfo:t2qc/mriqc/summary_csf_median': 'mriqc_summary_csf_median',
    'neuroinfo:t2qc/mriqc/summary_csf_n': 'mriqc_summary_csf_n',
    'neuroinfo:t2qc/mriqc/summary_csf_p05': 'mriqc_summary_csf_p05',
    'neuroinfo:t2qc/mriqc/summary_csf_p95': 'mriqc_summary_csf_p95',
    'neuroinfo:t2qc/mriqc/summary_csf_stdv': 'mriqc_summary_csf_stdv',
    'neuroinfo:t2qc/mriqc/summary_gm_k': 'mriqc_summary_gm_k',
    'neuroinfo:t2qc/mriqc/summary_gm_mad': 'mriqc_summary_gm_mad',
    'neuroinfo:t2qc/mriqc/summary_gm_mean': 'mriqc_summary_gm_mean',
    'neuroinfo:t2qc/mriqc/summary_gm_median': 'mriqc_summary_gm_median',
    'neuroinfo:t2qc/mriqc/summary_gm_n': 'mriqc_summary_gm_n',
    'neuroinfo:t2qc/mriqc/summary_gm_p05': 'mriqc_summary_gm_p05',
    'neuroinfo:t2qc/mriqc/summary_gm_p95': 'mriqc_summary_gm_p95',
    'neuroinfo:t2qc/mriqc/summary_gm_stdv': 'mriqc_summary_gm_stdv',
    'neuroinfo:t2qc/mriqc/summary_wm_k': 'mriqc_summary_wm_k',
    'neuroinfo:t2qc/mriqc/summary_wm_mad': 'mriqc_summary_wm_mad',
    'neuroinfo:t2qc/mriqc/summary_wm_mean': 'mriqc_summary_wm_mean',
    'neuroinfo:t2qc/mriqc/summary_wm_median': 'mriqc_summary_wm_median',
    'neuroinfo:t2qc/mriqc/summary_wm_n': 'mriqc_summary_wm_n',
    'neuroinfo:t2qc/mriqc/summary_wm_p05': 'mriqc_summary_wm_p05',
    'neuroinfo:t2qc/mriqc/summary_wm_p95': 'mriqc_summary_wm_p95',
    'neuroinfo:t2qc/mriqc/summary_wm_stdv': 'mriqc_summary_wm_stdv',
    'neuroinfo:t2qc/mriqc/tpm_overlap_csf': 'mriqc_tpm_overlap_csf',
    'neuroinfo:t2qc/mriqc/tpm_overlap_gm': 'mriqc_tpm_overlap_gm',
    'neuroinfo:t2qc/mriqc/tpm_overlap_wm': 'mriqc_tpm_overlap_wm',
    'neuroinfo:t2qc/mriqc/wm2max': 'mriqc_wm2max',
    'neuroinfo:t2qc/vnav/vnav_min': 'vnav_vnav_min',
    'neuroinfo:t2qc/vnav/vnav_max': 'vnav_vnav_max',
    'neuroinfo:t2qc/vnav/vnav_acq_tot': 'vnav_vnav_acq_tot',
    'neuroinfo:t2qc/vnav/vnav_reacq': 'vnav_vnav_reacq',
    'neuroinfo:t2qc/vnav/mean_mot_rms_per_min': 'vnav_mean_mot_rms_per_min',
    'neuroinfo:t2qc/vnav/mean_mot_max_per_min': 'vnav_mean_mot_max_per_min',
    'neuroinfo:t2qc/vnav/vnav_failed': 'vnav_vnav_failed',
    'neuroinfo:t2qc/manual/wrap': 'manual_wrap',
    'neuroinfo:t2qc/manual/cover': 'manual_cover',
    'neuroinfo:t2qc/manual/motion_brain': 'manual_motion_brain',
    'neuroinfo:t2qc/manual/motion_out': 'manual_motion_out',
    'neuroinfo:t2qc/manual/ghost_brain': 'manual_ghost_brain',
    'neuroinfo:t2qc/manual/ghost_out': 'manual_ghost_out',
    'neuroinfo:t2qc/manual/spike': 'manual_spike',
    'neuroinfo:t2qc/manual/art_brain': 'manual_art_brain',
    'neuroinfo:t2qc/manual/art_out': 'manual_art_out',
    'neuroinfo:t2qc/manual/inhom': 'manual_inhom',
    'neuroinfo:t2qc/manual/overall': 'manual_overall'
}

def anatqc(auth, label, scan_ids=None, project=None, aid=None):
    '''
    Get AnatQC data as a sequence of dictionaries.

    Example:
        >>> import json
        >>> import yaxil.assessments.neuroinfo as neuroinfo
        >>> auth = yaxil.auth('doctest')
        >>> for qc in neuroinfo.anatqc(auth, 'TestSession01'):
        ...   print(json.dumps(qc, indent=2))
        {
          "id": "TestSession01_ANAT_30_AQC",
          ...
        }

    :param auth: XNAT authentication object
    :type auth: :mod:`yaxil.XnatAuth`
    :param label: XNAT MR Session label
    :type label: str
    :param scan_ids: Scan numbers to include
    :type scan_ids: list
    :param project: XNAT MR Session project
    :type project: str
    :param aid: XNAT MR Session Accession ID
    :type aid: str
    :returns: Generator of AnatQC data dictionaries
    :rtype: :mod:`dict`
    '''
    if not aid:
        aid = yaxil.accession(auth, label, project)
    experiment_details = yaxil.__experiment_details(auth, aid)
    path = '/data/experiments'
    params = {
        'xsiType': 'neuroinfo:anatqc',
        'columns': ','.join(anatqc.columns.keys())
    }
    if project:
        params['project'] = project
    params['xnat:mrSessionData/ID'] = aid
    _,result = yaxil._get(auth, path, 'json', autobox=True, params=params)
    for result in result['ResultSet']['Result']:
        if scan_ids == None or result['neuroinfo:anatqc/t1w_scan_id'] in scan_ids:
            data = dict()
            for k,v in iter(anatqc.columns.items()):
                data[v] = result[k]
            files = __files(auth, result['neuroinfo:anatqc/id'])
            data.update(experiment_details)
            data['files'] = files
            yield data
anatqc.columns = {
    'neuroinfo:anatqc/id': 'ID',
    'neuroinfo:anatqc/id': 'id',
    'neuroinfo:anatqc/date': 'date',
    'neuroinfo:anatqc/time': 'time',
    'neuroinfo:anatqc/imagesession_id': 'session_id',
    'neuroinfo:anatqc/t1w_scan_id': 't1w_scan_id',
    'neuroinfo:anatqc/vnav_scan_id': 'vnav_scan_id',
    'neuroinfo:anatqc/session_label': 'session_label',
    'neuroinfo:anatqc/mriqc/cjv': 'mriqc_cjv',
    'neuroinfo:anatqc/mriqc/cnr': 'mriqc_cnr',
    'neuroinfo:anatqc/mriqc/efc': 'mriqc_efc',
    'neuroinfo:anatqc/mriqc/fber': 'mriqc_fber',
    'neuroinfo:anatqc/mriqc/fwhm_avg': 'mriqc_fwhm_avg',
    'neuroinfo:anatqc/mriqc/fwhm_x': 'mriqc_fwhm_x',
    'neuroinfo:anatqc/mriqc/fwhm_y': 'mriqc_fwhm_y',
    'neuroinfo:anatqc/mriqc/fwhm_z': 'mriqc_fwhm_z',
    'neuroinfo:anatqc/mriqc/icvs_csf': 'mriqc_icvs_csf',
    'neuroinfo:anatqc/mriqc/icvs_gm': 'mriqc_icvs_gm',
    'neuroinfo:anatqc/mriqc/icvs_wm': 'mriqc_icvs_wm',
    'neuroinfo:anatqc/mriqc/inu_med': 'mriqc_inu_med',
    'neuroinfo:anatqc/mriqc/inu_range': 'mriqc_inu_range',
    'neuroinfo:anatqc/mriqc/qi_1': 'mriqc_qi_1',
    'neuroinfo:anatqc/mriqc/qi_2': 'mriqc_qi_2',
    'neuroinfo:anatqc/mriqc/rpve_csf': 'mriqc_rpve_csf',
    'neuroinfo:anatqc/mriqc/rpve_gm': 'mriqc_rpve_gm',
    'neuroinfo:anatqc/mriqc/rpve_wm': 'mriqc_rpve_wm',
    'neuroinfo:anatqc/mriqc/size_x': 'mriqc_size_x',
    'neuroinfo:anatqc/mriqc/size_y': 'mriqc_size_y',
    'neuroinfo:anatqc/mriqc/size_z': 'mriqc_size_z',
    'neuroinfo:anatqc/mriqc/snr_csf': 'mriqc_snr_csf',
    'neuroinfo:anatqc/mriqc/snr_gm': 'mriqc_snr_gm',
    'neuroinfo:anatqc/mriqc/snr_total': 'mriqc_snr_total',
    'neuroinfo:anatqc/mriqc/snr_wm': 'mriqc_snr_wm',
    'neuroinfo:anatqc/mriqc/snrd_csf': 'mriqc_snrd_csf',
    'neuroinfo:anatqc/mriqc/snrd_gm': 'mriqc_snrd_gm',
    'neuroinfo:anatqc/mriqc/snrd_total': 'mriqc_snrd_total',
    'neuroinfo:anatqc/mriqc/snrd_wm': 'mriqc_snrd_wm',
    'neuroinfo:anatqc/mriqc/spacing_x': 'mriqc_spacing_x',
    'neuroinfo:anatqc/mriqc/spacing_y': 'mriqc_spacing_y',
    'neuroinfo:anatqc/mriqc/spacing_z': 'mriqc_spacing_z',
    'neuroinfo:anatqc/mriqc/summary_bg_k': 'mriqc_summary_bg_k',
    'neuroinfo:anatqc/mriqc/summary_bg_mad': 'mriqc_summary_bg_mad',
    'neuroinfo:anatqc/mriqc/summary_bg_mean': 'mriqc_summary_bg_mean',
    'neuroinfo:anatqc/mriqc/summary_bg_median': 'mriqc_summary_bg_median',
    'neuroinfo:anatqc/mriqc/summary_bg_n': 'mriqc_summary_bg_n',
    'neuroinfo:anatqc/mriqc/summary_bg_p05': 'mriqc_summary_bg_p05',
    'neuroinfo:anatqc/mriqc/summary_bg_p95': 'mriqc_summary_bg_p95',
    'neuroinfo:anatqc/mriqc/summary_bg_stdv': 'mriqc_summary_bg_stdv',
    'neuroinfo:anatqc/mriqc/summary_csf_k': 'mriqc_summary_csf_k',
    'neuroinfo:anatqc/mriqc/summary_csf_mad': 'mriqc_summary_csf_mad',
    'neuroinfo:anatqc/mriqc/summary_csf_mean': 'mriqc_summary_csf_mean',
    'neuroinfo:anatqc/mriqc/summary_csf_median': 'mriqc_summary_csf_median',
    'neuroinfo:anatqc/mriqc/summary_csf_n': 'mriqc_summary_csf_n',
    'neuroinfo:anatqc/mriqc/summary_csf_p05': 'mriqc_summary_csf_p05',
    'neuroinfo:anatqc/mriqc/summary_csf_p95': 'mriqc_summary_csf_p95',
    'neuroinfo:anatqc/mriqc/summary_csf_stdv': 'mriqc_summary_csf_stdv',
    'neuroinfo:anatqc/mriqc/summary_gm_k': 'mriqc_summary_gm_k',
    'neuroinfo:anatqc/mriqc/summary_gm_mad': 'mriqc_summary_gm_mad',
    'neuroinfo:anatqc/mriqc/summary_gm_mean': 'mriqc_summary_gm_mean',
    'neuroinfo:anatqc/mriqc/summary_gm_median': 'mriqc_summary_gm_median',
    'neuroinfo:anatqc/mriqc/summary_gm_n': 'mriqc_summary_gm_n',
    'neuroinfo:anatqc/mriqc/summary_gm_p05': 'mriqc_summary_gm_p05',
    'neuroinfo:anatqc/mriqc/summary_gm_p95': 'mriqc_summary_gm_p95',
    'neuroinfo:anatqc/mriqc/summary_gm_stdv': 'mriqc_summary_gm_stdv',
    'neuroinfo:anatqc/mriqc/summary_wm_k': 'mriqc_summary_wm_k',
    'neuroinfo:anatqc/mriqc/summary_wm_mad': 'mriqc_summary_wm_mad',
    'neuroinfo:anatqc/mriqc/summary_wm_mean': 'mriqc_summary_wm_mean',
    'neuroinfo:anatqc/mriqc/summary_wm_median': 'mriqc_summary_wm_median',
    'neuroinfo:anatqc/mriqc/summary_wm_n': 'mriqc_summary_wm_n',
    'neuroinfo:anatqc/mriqc/summary_wm_p05': 'mriqc_summary_wm_p05',
    'neuroinfo:anatqc/mriqc/summary_wm_p95': 'mriqc_summary_wm_p95',
    'neuroinfo:anatqc/mriqc/summary_wm_stdv': 'mriqc_summary_wm_stdv',
    'neuroinfo:anatqc/mriqc/tpm_overlap_csf': 'mriqc_tpm_overlap_csf',
    'neuroinfo:anatqc/mriqc/tpm_overlap_gm': 'mriqc_tpm_overlap_gm',
    'neuroinfo:anatqc/mriqc/tpm_overlap_wm': 'mriqc_tpm_overlap_wm',
    'neuroinfo:anatqc/mriqc/wm2max': 'mriqc_wm2max',
    'neuroinfo:anatqc/morph/mri_cnr_tot': 'morph_mri_cnr_tot',
    'neuroinfo:anatqc/morph/wm_anat_snr': 'morph_wm_anat_snr',
    'neuroinfo:anatqc/morph/lh_euler_holes': 'morph_lh_euler_holes',
    'neuroinfo:anatqc/morph/lh_cnr': 'morph_lh_cnr',
    'neuroinfo:anatqc/morph/lh_gm_wm_cnr': 'morph_lh_gm_wm_cnr',
    'neuroinfo:anatqc/morph/lh_gm_csf_cnr': 'morph_lh_gm_csf_cnr',
    'neuroinfo:anatqc/morph/rh_euler_holes': 'morph_rh_euler_holes',
    'neuroinfo:anatqc/morph/rh_cnr': 'morph_rh_cnr',
    'neuroinfo:anatqc/morph/rh_gm_wm_cnr': 'morph_rh_gm_wm_cnr',
    'neuroinfo:anatqc/morph/rh_gm_csf_cnr': 'morph_rh_gm_csf_cnr',    
    'neuroinfo:anatqc/vnav/vnav_min': 'vnav_vnav_min',
    'neuroinfo:anatqc/vnav/vnav_max': 'vnav_vnav_max',
    'neuroinfo:anatqc/vnav/vnav_acq_tot': 'vnav_vnav_acq_tot',
    'neuroinfo:anatqc/vnav/vnav_reacq': 'vnav_vnav_reacq',
    'neuroinfo:anatqc/vnav/mean_mot_rms_per_min': 'vnav_mean_mot_rms_per_min',
    'neuroinfo:anatqc/vnav/mean_mot_max_per_min': 'vnav_mean_mot_max_per_min',
    'neuroinfo:anatqc/vnav/vnav_failed': 'vnav_vnav_failed',
    'neuroinfo:anatqc/manual/wrap': 'manual_wrap',
    'neuroinfo:anatqc/manual/cover': 'manual_cover',
    'neuroinfo:anatqc/manual/motion_brain': 'manual_motion_brain',
    'neuroinfo:anatqc/manual/motion_out': 'manual_motion_out',
    'neuroinfo:anatqc/manual/ghost_brain': 'manual_ghost_brain',
    'neuroinfo:anatqc/manual/ghost_out': 'manual_ghost_out',
    'neuroinfo:anatqc/manual/spike': 'manual_spike',
    'neuroinfo:anatqc/manual/art_brain': 'manual_art_brain',
    'neuroinfo:anatqc/manual/art_out': 'manual_art_out',
    'neuroinfo:anatqc/manual/inhom': 'manual_inhom',
    'neuroinfo:anatqc/manual/overall': 'manual_overall'
}

def __files(auth, aid):
    path = f'/data/experiments/{aid}/files'
    _,result = yaxil._get(auth, path, 'json', autobox=True)
    files = dict()
    for result in result['ResultSet']['Result']:
        name = result['URI'].split('/')[-2]
        files[name] = result
    return files 

if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

