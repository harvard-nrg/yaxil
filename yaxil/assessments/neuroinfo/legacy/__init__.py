import yaxil

def boldqc(auth, label=None, scan_ids=None, project=None, aid=None):
    '''
    Get BOLDQC data as a sequence of dictionaries.

    Example:
        >>> import json
        >>> import yaxil.assessments.neuroinfo.legacy as neuroinfo
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
        'xsiType': 'neuroinfo:extendedboldqc',
        'columns': ','.join(boldqc.columns.keys())
    }
    if project:
        params['project'] = project
    params['xnat:mrSessionData/ID'] = aid
    _,result = yaxil._get(auth, path, 'json', autobox=True, params=params)
    for result in result['ResultSet']['Result']:
        assessor = result['neuroinfo:extendedboldqc/id']
        if scan_ids == None or result['neuroinfo:extendedboldqc/scan/scan_id'] in scan_ids:
            data = dict()
            for k,v in iter(boldqc.columns.items()):
                data[v] = result[k]
            files = __files(
                auth,
                experiment_details['session_project'],
                experiment_details['subject_label'],
                experiment_details['session_label'],
                assessor
            )
            data.update(experiment_details)
            data['files'] = files
            yield data
boldqc.columns = {
    'neuroinfo:extendedboldqc/id': 'ID',
    'neuroinfo:extendedboldqc/id': 'id',
    'neuroinfo:extendedboldqc/date': 'date',
    'neuroinfo:extendedboldqc/time': 'time',
    'neuroinfo:extendedboldqc/imagesession_id': 'session_id',
    'neuroinfo:extendedboldqc/scan/scan_id': 'bold_scan_id',
    'neuroinfo:extendedboldqc/scan/size': 'size',
    'neuroinfo:extendedboldqc/scan/n_vols': 'n_vols',
    'neuroinfo:extendedboldqc/scan/skip': 'skip',
    'neuroinfo:extendedboldqc/scan/qc_n_tps': 'qc_n_tps',
    'neuroinfo:extendedboldqc/scan/qc_thresh': 'qc_thresh',
    'neuroinfo:extendedboldqc/scan/qc_nvox': 'qc_nvox',
    'neuroinfo:extendedboldqc/scan/qc_mean': 'qc_mean',
    'neuroinfo:extendedboldqc/scan/qc_max': 'qc_max',
    'neuroinfo:extendedboldqc/scan/qc_min': 'qc_min',
    'neuroinfo:extendedboldqc/scan/qc_stdev': 'qc_stdev',
    'neuroinfo:extendedboldqc/scan/qc_ssnr': 'qc_ssnr',
    'neuroinfo:extendedboldqc/scan/qc_vsnr': 'qc_vsnr',
    'neuroinfo:extendedboldqc/scan/qc_slope': 'qc_slope',
    'neuroinfo:extendedboldqc/scan/mot_n_tps': 'mot_n_tps',
    'neuroinfo:extendedboldqc/scan/mot_rel_x_mean': 'mot_rel_x_mean',
    'neuroinfo:extendedboldqc/scan/mot_rel_x_sd': 'mot_rel_x_sd',
    'neuroinfo:extendedboldqc/scan/mot_rel_x_max': 'mot_rel_x_max',
    'neuroinfo:extendedboldqc/scan/mot_rel_x_1mm': 'mot_rel_x_1mm',
    'neuroinfo:extendedboldqc/scan/mot_rel_x_5mm': 'mot_rel_x_5mm',
    'neuroinfo:extendedboldqc/scan/mot_rel_y_mean': 'mot_rel_y_mean',
    'neuroinfo:extendedboldqc/scan/mot_rel_y_sd': 'mot_rel_y_sd',
    'neuroinfo:extendedboldqc/scan/mot_rel_y_max': 'mot_rel_y_max',
    'neuroinfo:extendedboldqc/scan/mot_rel_y_1mm': 'mot_rel_y_1mm',
    'neuroinfo:extendedboldqc/scan/mot_rel_y_5mm': 'mot_rel_y_5mm',
    'neuroinfo:extendedboldqc/scan/mot_rel_z_mean': 'mot_rel_z_mean',
    'neuroinfo:extendedboldqc/scan/mot_rel_z_sd': 'mot_rel_z_sd',
    'neuroinfo:extendedboldqc/scan/mot_rel_z_max': 'mot_rel_z_max',
    'neuroinfo:extendedboldqc/scan/mot_rel_z_1mm': 'mot_rel_z_1mm',
    'neuroinfo:extendedboldqc/scan/mot_rel_z_5mm': 'mot_rel_z_5mm',
    'neuroinfo:extendedboldqc/scan/mot_rel_xyz_mean': 'mot_rel_xyz_mean',
    'neuroinfo:extendedboldqc/scan/mot_rel_xyz_sd': 'mot_rel_xyz_sd',
    'neuroinfo:extendedboldqc/scan/mot_rel_xyz_max': 'mot_rel_xyz_max',
    'neuroinfo:extendedboldqc/scan/mot_rel_xyz_1mm': 'mot_rel_xyz_1mm',
    'neuroinfo:extendedboldqc/scan/mot_rel_xyz_5mm': 'mot_rel_xyz_5mm',
    'neuroinfo:extendedboldqc/scan/rot_rel_x_mean': 'rot_rel_x_mean',
    'neuroinfo:extendedboldqc/scan/rot_rel_x_sd': 'rot_rel_x_sd',
    'neuroinfo:extendedboldqc/scan/rot_rel_x_max': 'rot_rel_x_max',
    'neuroinfo:extendedboldqc/scan/rot_rel_y_mean': 'rot_rel_y_mean',
    'neuroinfo:extendedboldqc/scan/rot_rel_y_sd': 'rot_rel_y_sd',
    'neuroinfo:extendedboldqc/scan/rot_rel_y_max': 'rot_rel_y_max',
    'neuroinfo:extendedboldqc/scan/rot_rel_z_mean': 'rot_rel_z_mean',
    'neuroinfo:extendedboldqc/scan/rot_rel_z_sd': 'rot_rel_z_sd',
    'neuroinfo:extendedboldqc/scan/rot_rel_z_max': 'rot_rel_z_max',
    'neuroinfo:extendedboldqc/scan/mot_abs_x_mean': 'mot_abs_x_mean',
    'neuroinfo:extendedboldqc/scan/mot_abs_x_sd': 'mot_abs_x_sd',
    'neuroinfo:extendedboldqc/scan/mot_abs_x_max': 'mot_abs_x_max',
    'neuroinfo:extendedboldqc/scan/mot_abs_y_mean': 'mot_abs_y_mean',
    'neuroinfo:extendedboldqc/scan/mot_abs_y_sd': 'mot_abs_y_sd',
    'neuroinfo:extendedboldqc/scan/mot_abs_y_max': 'mot_abs_y_max',
    'neuroinfo:extendedboldqc/scan/mot_abs_z_mean': 'mot_abs_z_mean',
    'neuroinfo:extendedboldqc/scan/mot_abs_z_sd': 'mot_abs_z_sd',
    'neuroinfo:extendedboldqc/scan/mot_abs_z_max': 'mot_abs_z_max',
    'neuroinfo:extendedboldqc/scan/mot_abs_xyz_mean': 'mot_abs_xyz_mean',
    'neuroinfo:extendedboldqc/scan/mot_abs_xyz_sd': 'mot_abs_xyz_sd',
    'neuroinfo:extendedboldqc/scan/mot_abs_xyz_max': 'mot_abs_xyz_max',
    'neuroinfo:extendedboldqc/scan/rot_abs_x_mean': 'rot_abs_x_mean',
    'neuroinfo:extendedboldqc/scan/rot_abs_x_sd': 'rot_abs_x_sd',
    'neuroinfo:extendedboldqc/scan/rot_abs_x_max': 'rot_abs_x_max',
    'neuroinfo:extendedboldqc/scan/rot_abs_y_mean': 'rot_abs_y_mean',
    'neuroinfo:extendedboldqc/scan/rot_abs_y_sd': 'rot_abs_y_sd',
    'neuroinfo:extendedboldqc/scan/rot_abs_y_max': 'rot_abs_y_max',
    'neuroinfo:extendedboldqc/scan/rot_abs_z_mean': 'rot_abs_z_mean',
    'neuroinfo:extendedboldqc/scan/rot_abs_z_sd': 'rot_abs_z_sd',
    'neuroinfo:extendedboldqc/scan/rot_abs_z_max': 'rot_abs_z_max'
    
}

def __files(auth, project, subject, experiment, assessor):
    path = f'/data/projects/{project}/subjects/{subject}/experiments/{experiment}/assessors/{assessor}/files'
    _,result = yaxil._get(auth, path, 'json', autobox=True)
    files = dict()
    for result in result['ResultSet']['Result']:
        name = result['file_content']
        files[name] = result
    return files 

if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

