import io
import os
import csv
import sys
import gzip
import json
import time
import arrow
import random
import sqlite3
import zipfile
import logging
import requests
import itertools
import getpass as gp
import tempfile as tf
import subprocess as sp
import collections as col
from argparse import Namespace
from contextlib import contextmanager
import xml.etree.ElementTree as etree

import yaxil.commons as commons
import yaxil.functools as functools
from yaxil.session import Session
from yaxil.exceptions import ( AuthError, MultipleAccessionError,  NoAccessionError,
                               AccessionError, DownloadError, ResultSetError,
                               ScanSearchError, EQCNotFoundError, RestApiError,
                               AutoboxError, NoExperimentsError, NoSubjectsError,
                               CommandNotFoundError )

# Whether to verify SSL certificates. Primarily of use during testing.
CHECK_CERTIFICATE = True

logger = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)

class Format(object):
    '''
    A container to hold possible XNAT response formats ``Format.JSON``,
    ``Format.XML``, and ``Format.CSV``.
    '''
    JSON  = "json"
    XML   = "xml"
    CSV   = "csv"

class Response:
    '''
    Container for response content
    '''
    def __init__(self, url, content):
        self.url = url
        self.content = content

XnatAuth = col.namedtuple("XnatAuth", [
    "url",
    "username",
    "password",
    "cookie"
])
'''
Container to hold XNAT authentication information. Fields include the ``url``,
``username``, and ``password``.
'''

def test_auth(auth):
    '''
    Validate credentials against XNAT

    Example:
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> yaxil.test_auth(auth)
        True
    '''
    baseurl = auth.url.rstrip('/')
    url = f'{baseurl}/data/projects'
    r = requests.get(
        url,
        auth=basicauth(auth),
        params={
            'columns': 'ID'
        }
    )
    if r.status_code == requests.codes.UNAUTHORIZED:
        return False
    return True

def start_session(auth):
    '''
    Return auth object with populated authentication cookie (JSESSIONID)
    '''
    baseurl = auth.url.rstrip('/')
    url = f'{baseurl}/data/JSESSION'
    r = requests.get(
        url,
        auth=basicauth(auth),
        cookies=auth.cookie,
        verify=CHECK_CERTIFICATE
    )
    if r.status_code != requests.codes.ok:
        raise SessionError(f'response not ok ({r.status_code}) from {r.url}')
    return XnatAuth(
        username=auth.username,
        password=auth.password,
        url=auth.url,
        cookie={
            'JSESSIONID': r.text
        }
    )

def end_session(auth):
    if not auth.cookie:
        return
    baseurl = auth.url.rstrip('/')
    url = f'{baseurl}/data/JSESSION'
    r = requests.delete(
        url,
        auth=basicauth(auth),
        cookies=auth.cookie,
        verify=CHECK_CERTIFICATE
    )
    if r.status_code != requests.codes.ok:
        raise SessionError('response not ok ({0}) from {1}'.format(r.status_code, r.url))

class SessionError(Exception):
    pass

def basicauth(auth):
    '''
    Create basic auth tuple for requests.
    '''
    if auth.username and auth.password:
        return (auth.username, auth.password)
    return None

def session(auth):
    '''
    Create a session context to avoid passing `auth` to
    every function.

    Example:
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> with yaxil.session(auth) as ses:
        ...   aid = ses.accession('TestSession01')
        ...   print(aid)
        XNAT_E...

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :returns: YAXIL session object
    :rtype: :mod:`yaxil.session.Session`
    '''
    return Session(auth)

def auth2(alias=None, host=None, username=None, password=None, cfg='~/.xnat_auth'):
    '''
    Create authentication object from an ``xnat_auth`` file, function arguments, 
    or environment variables (``XNAT_HOST``, ``XNAT_USER``, and ``XNAT_PASS``), 
    in that order

    Example:
        >>> import os
        >>> import yaxil
        >>> os.environ['XNAT_HOST'] = 'https://xnat.example.com'
        >>> os.environ['XNAT_USER'] = 'username'
        >>> os.environ['XNAT_PASS'] = '*****'
        >>> yaxil.auth2()
        XnatAuth(url='https://xnat.example.com', username='username', password='*****')
    '''
    result = tuple()
    # First, look for authentication data in ~/.xnat_auth
    if alias:
        logger.debug(f'returning authentication data from {cfg}')
        return auth(alias)
    # Second, look for authentication data from --host, --user, --password function arguments
    authargs = (host, username)
    if any(authargs):
        if not all(authargs):
            raise AuthError('you must supply --host, --username and --password (or password prompt)')
        logger.debug('returning authentication data from command line')
        if not password:
            password = gp.getpass('Enter XNAT passphrase:')
        obj = XnatAuth(
            url=host,
            username=username,
            password=password,
            cookie=None
        )
        return start_session(obj)
    # Third, look for authentication data in environment variables
    host = os.environ.get('XNAT_HOST', None)
    username = os.environ.get('XNAT_USER', None)
    password = os.environ.get('XNAT_PASS', None)
    authargs = (host, username)
    if any(authargs):
        if not all(authargs):
            raise AuthError('you must set $XNAT_HOST, $XNAT_USER, and $XNAT_PASS (or password prompt)')
        logger.debug('returning authentication data from environment variables')
        if not password:
            password = gp.getpass('Enter XNAT passphrase:')
        obj = XnatAuth(
            url=host,
            username=username,
            password=password,
            cookie=None
        )
        return start_session(obj)
    raise AuthError('you must provide authentication data using xnat_auth, command line, or environment variables')

def auth(alias=None, url=None, cfg="~/.xnat_auth"):
    '''
    Read connection details from an xnat_auth XML file

    Example:
        >>> import yaxil
        >>> yaxil.auth('doctest')
        XnatAuth(url='...', username='...', password='...')

    :param alias: XNAT alias
    :type alias: str
    :param url: XNAT URL
    :type url: str
    :param cfg: Configuration file
    :type cfg: str
    :returns: Named tuple of (url, username, password)
    :rtype: :mod:`yaxil.XnatAuth`
    '''
    if not alias and not url:
        raise ValueError('you must provide an alias or url argument')
    if alias and url:
        raise ValueError('cannot provide both alias and url arguments')
    # check and parse config file
    cfg = os.path.expanduser(cfg)
    if not os.path.exists(cfg):
        raise AuthError("could not locate auth file %s" % cfg)
    tree = etree.parse(os.path.expanduser(cfg))
    # search by alias or url
    res = None
    if alias:
        res = tree.findall("./%s" % alias)
    if url:
        res = tree.findall("./*/[url='%s']" % url)
    if not res:
        raise AuthError("failed to locate xnat credentials within %s" % cfg)
    elif len(res) > 1:
        raise AuthError("found too many sets of credentials within %s" % cfg)
    res = res.pop()
    # get url
    url = res.findall("url")
    if not url:
        raise AuthError("no url for %s in %s" % (alias, cfg))
    elif len(url) > 1:
        raise AuthError("too many urls for %s in %s" % (alias, cfg))
    # get username
    username = res.findall("username")
    if not username:
        raise AuthError("no username for %s in %s" % (alias, cfg))
    elif len(username) > 1:
        raise AuthError("too many usernames for %s in %s" % (alias, cfg))
    # get password
    password = res.findall("password")
    if not password:
        password = gp.getpass('Enter XNAT passphrase:')
    elif len(password) > 1:
        raise AuthError("too many passwords for %s in %s" % (alias, cfg))
    else:
        password = password.pop().text
    obj = XnatAuth(
        url=url.pop().text,
        username=username.pop().text,
        password=password,
        cookie=None
    )
    return start_session(obj)

Subject = col.namedtuple('Subject', [
    'uri',
    'label',
    'id',
    'project'
])
'''
Container to hold XNAT Subject information. Fields include the Subject URI
``uri``, Accession ID ``id``, Project ``project``, and Label ``label``.
'''

def subjects(auth, label=None, project=None):
    '''
    Retrieve Subject tuples for subjects returned by this function.

    Example:
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> for subject in yaxil.subjects(auth, project='TestProject01'):
        ...   print(subject)
        Subject(uri='/data/subjects/XNAT_S...', label='...',
            id='XNAT_S...', project='TestProject01')

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :param label: XNAT Subject label
    :type label: str
    :param project: XNAT Subject Project
    :type project: str
    :returns: Subject objects
    :rtype: :mod:`yaxil.Subject`
    '''
    url = '{0}/data/subjects'.format(auth.url.rstrip('/'))
    logger.debug('issuing http request %s', url)
    # compile query string
    columns = [
        'ID',
        'label',
        'project'
    ]
    payload = {
        'columns': ','.join(columns)
    }
    if label:
        payload['label'] = label
    if project:
        payload['project'] = project
    # submit the request
    r = requests.get(
        url,
        params=payload,
        auth=basicauth(auth),
        cookies=auth.cookie,
        verify=CHECK_CERTIFICATE
    )
    # validate response
    if r.status_code != requests.codes.ok:
        raise AccessionError(f'response not ok ({r.status_code} {r.reason}) from {r.url}')
    try:
        results = r.json()
        __quick_validate(results)
    except ResultSetError as e:
        raise ResultSetError('{0} from {1}'.format(e.message, r.url))
    results = results['ResultSet']
    if int(results['totalRecords']) == 0:
        raise NoSubjectsError('no records returned from {0}'.format(r.url))
    # start generating consumable results for the caller
    for item in results['Result']:
        yield Subject(uri=item['URI'],
                      id=item['ID'],
                      project=item['project'],
                      label=item['label'])

Experiment = col.namedtuple('Experiment', [
    'uri',
    'label',
    'id',
    'project',
    'subject_id',
    'subject_label',
    'archived_date',
    'note'
])
'''
Container to hold XNAT Experiment information. Fields include the Experiment URI
``uri``, Accession ID ``id``, Project ``project``, Label ``label``, Subject 
Accession ID ``subject_id``, Subject label ``subject_label``, and archive date 
``archived_date``.
'''

def experiments(auth, label=None, project=None, subject=None, daterange=None):
    '''
    Retrieve Experiment tuples for experiments returned by this function.

    Example:
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> for experiment in yaxil.experiments(auth, 'TestSession01'):
        ...   print(experiment)
        Experiment(uri='...', label='...', id='...', project='...', 
          subject_id='...', subject_label='...', archived_date='...')
        >>>

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :param label: XNAT Experiment label
    :type label: str
    :param project: XNAT Experiment Project
    :type project: str
    :param subject: YAXIL Subject
    :type subject: :mod:`yaxil.Subject`
    :param daterange: Start and end dates
    :type daterange: tuple
    :returns: Experiment object
    :rtype: :mod:`yaxil.Experiment`
    '''
    if subject and (label or project):
        raise ValueError('cannot provide subject with label or project')
    url = '{0}/data/experiments'.format(auth.url.rstrip('/'))
    logger.debug('issuing http request %s', url)
    columns = [
        'ID',
        'label',
        'project',
        'xnat:subjectassessordata/subject_id',
        'subject_label',
        'insert_date',
        'note'
    ]
    payload = {
        'columns': ','.join(columns)
    }
    if label:
        payload['label'] = label
    if project:
        payload['project'] = project
    if subject:
        payload['project'] = subject.project
        payload['xnat:subjectassessordata/subject_id'] = subject.id
    if daterange:
        start = arrow.get(daterange[0]).format('MM/DD/YYYY')
        stop = arrow.get(daterange[1]).format('MM/DD/YYYY')
        payload['date'] = '{0}-{1}'.format(start, stop)
    # submit request
    r = requests.get(
        url,
        params=payload,
        auth=basicauth(auth),
        cookies=auth.cookie,
        verify=CHECK_CERTIFICATE
    )
    # validate response
    if r.status_code != requests.codes.ok:
        raise AccessionError(f'response not ok ({r.status_code} {r.reason}) from {r.url}')
    try:
        results = r.json()
        __quick_validate(results)
    except ResultSetError as e:
        raise ResultSetError('{0} from {1}'.format(e.message, r.url))
    results = results['ResultSet']
    if int(results['totalRecords']) == 0:
        raise NoExperimentsError('no records returned for {0}'.format(r.url))
    for item in results['Result']:
        yield Experiment(
            uri=item['URI'],
            id=item['ID'],
            project=item['project'],
            label=item['label'],
            subject_id=item['subject_ID'],
            subject_label=item['subject_label'],
            archived_date=item['insert_date'],
            note=item['note']
        )

@functools.lru_cache
def accession(auth, label, project=None):
    '''
    Get the Accession ID for any Experiment.

    Example:
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> yaxil.accession(auth, 'TestSession01')
        'XNAT_E...'

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :param label: XNAT Experiment label
    :type label: str
    :param project: XNAT Experiment Project
    :type project: str
    :returns: Accession ID
    :rtype: str
    '''
    expts = list(experiments(auth, label, project))
    if len(expts) > 1:
        raise MultipleAccessionError(f'label={label}, project={project}')
    return expts[0].id

def download(auth, label, scan_ids=None, project=None, aid=None,
             out_dir='.', in_mem=True, progress=False, attempts=1,
             out_format='flat'):
    '''
    Download scan data from XNAT.

    Example:
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> yaxil.download(auth, 'TestSession01', ['1', '2'], out_dir='./data')

    :param auth: XNAT authentication object
    :type auth: :mod:`yaxil.XnatAuth`
    :param label: XNAT MR Session label
    :type label: str
    :param scan_ids: Scan numbers to return; use None for all
    :type scan_ids: list
    :param project: XNAT MR Session project
    :type project: str
    :param aid: XNAT Accession ID
    :type aid: str
    :param out_dir: Output directory
    :type out_dir: str
    :param out_format: Extract all files or leave native structure
    :type output_format: str
    :param in_mem: Keep download content in memory; faster but uses more memory
    :type in_mem: bool
    :param progress: Show download progress every N bytes
    :type progress: int
    :param attempts: Number of download attempts
    :type attempts: int
    '''
    if not scan_ids:
        scan_ids = ['ALL']
    if not aid:
        aid = accession(auth, label, project)
    # build the url
    url = "%s/data/experiments/%s/scans/%s/files?format=zip" % (auth.url.rstrip('/'),
            aid, ','.join([str(x) for x in scan_ids]))
    # issue the http request, with exponential backoff retry behavior
    backoff = 10
    for _ in range(attempts):
        logger.debug("issuing http request %s", url)
        r = requests.get(
            url,
            stream=True,
            auth=basicauth(auth),
            cookies=auth.cookie,
            verify=CHECK_CERTIFICATE
        )
        logger.debug("response headers %s", r.headers)
        if r.status_code == requests.codes.ok:
            break
        fuzz = random.randint(0, 10)
        logger.warning("download unsuccessful (%s), retrying in %s seconds", r.status_code,
            backoff + fuzz)
        time.sleep(backoff + fuzz)
        backoff *= 2
    # if we still have a not-ok status at this point, the download failed
    if r.status_code != requests.codes.ok:
        raise DownloadError(f'response not ok ({r.status_code} {r.reason}) from {r.url}')
    # create output directory
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    # keep response content in memory or write to a file (memory is obviously faster, but limited)
    if in_mem:
        content = io.BytesIO()
        logger.debug("response content will be read into memory")
    else:
        content = tf.NamedTemporaryFile(dir=out_dir, prefix="xnat", suffix=".zip")
        logger.debug("response content will be stored on disk %s", content.name)
    # progress indicator setup
    if progress:
        sys.stdout.write("reading response data: ")
        sys.stdout.flush()
    # read response content in chunks
    meter = 0
    chunk_size = 1024
    for chunk in r.iter_content(chunk_size=chunk_size):
        if progress and meter >= progress:
            sys.stdout.write(next(commons.spinner)); sys.stdout.flush()
            sys.stdout.write('\b')
            meter = 0
        content.write(chunk)
        meter += chunk_size
    # flush and fsync before moving on
    content.flush()
    try:
        os.fsync(content.fileno())
    except io.UnsupportedOperation:
        pass
    # progress indicator shut down
    if progress:
        sys.stdout.write('done.\n'); sys.stdout.flush()
    # load reponse content into a zipfile object
    try:
        zf = zipfile.ZipFile(content, allowZip64=True)
    except zipfile.BadZipfile:
        with tf.NamedTemporaryFile(dir=out_dir, prefix="xnat",
                                   suffix=".zip", delete=False) as fo:
            content.seek(0)
            fo.write(content.read())
            fo.flush()
            os.fsync(fo.fileno())
        raise DownloadError("bad zip file, written to %s" % fo.name)
    # finally extract the zipfile (with various nasty edge cases handled)
    logger.debug("extracting zip archive to %s", out_dir)

    if out_format == 'native':
        zf.extractall(path=out_dir)
    else:  # out_format == 'flat' or out_format == '1.4'
        extract(zf, content, out_dir)


def extract(zf, content, out_dir='.'):
    '''
    Extracting a Java 1.6 XNAT ZIP archive in Python.

    :param zf: ZipFile object
    :type zf: zipfile.ZipFile
    :param out_dir: Output directory
    :type out_dir: str
    '''
    previous_header_offset = 0
    compensation = Namespace(value=2**32, factor=0)
    for i,member in enumerate(zf.infolist()):
        '''
        Right... so when Java 1.6 produces a Zip filesystem that exceeds 2^32
        bytes, the Central Directory local file header offsets after the 2^32
        byte appear to overflow. The Python zipfile module then adds any
        unexpected bytes to each header offset thereafter. This attempts to fix
        that. My guess is that this comment might make perfect sense now, but
        will make aboslutely no sense in about a year.
        '''
        # undo concat padding added from zipfile.py:819
        if i == 0:
            concat = member.header_offset
        member.header_offset -= concat
        # if a header offset moves backward, add 2^32 bytes * factor
        if previous_header_offset > member.header_offset:
            compensation.factor += 1
        previous_header_offset = member.header_offset
        member.header_offset += compensation.value * compensation.factor
        # read the archive member into a bytes file-like object
        try:
            bio = io.BytesIO(zf.read(member.filename))
        except zipfile.BadZipfile:
            with tf.NamedTemporaryFile(dir=out_dir, prefix="xnat",
                                   suffix=".zip", delete=False) as fo:
                content.seek(0)
                fo.write(content.read())
                fo.flush()
                os.fsync(fo.fileno())
            raise DownloadError("bad zip file, written to %s" % fo.name)
        # xnat archives may contain files that are gzipped without the .gz
        if not member.filename.endswith(".gz"):
            try:
                gz = gzip.GzipFile(fileobj=bio, mode="rb")
                gz.read()
                bio = gz
            except IOError:
                pass
        # write the file out to the filesystem
        bio.seek(0)
        f = os.path.join(out_dir, os.path.basename(member.filename))
        commons.atomic_write(f, bio.read(), encoding=False)

def __quick_validate(r, check=('ResultSet', 'Result', 'totalRecords')):
    '''
    Quick validation of JSON result set returned by XNAT.

    :param r: Result set data in JSON format
    :type r: dict
    :param check: Fields to check
    :type check: tuple
    :returns: Result set is valid
    :rtype: bool
    '''
    if 'ResultSet' in check and 'ResultSet' not in r:
        raise ResultSetError('no ResultSet in server response')
    if 'Result' in check and 'Result' not in r['ResultSet']:
        raise ResultSetError('no Result in server response')
    if 'totalRecords' in check and 'totalRecords' not in r['ResultSet']:
        raise ResultSetError('no totalRecords in server response')
    return True

def scansearch(auth, label, filt, project=None, aid=None):
    '''
    Search for scans by supplying a set of SQL-based conditionals.

    Example:
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> query = {
        ...   'sr': 'note LIKE "%Structured Report%"',
        ...   'anat': 'series_description="t1_mpr_1mm_p2_pos50" OR note LIKE "%ANAT%"'
        ... }
        >>> result = yaxil.scansearch(auth, 'TestSession01', query)
        >>> print(json.dumps(result, indent=2))
        {
          "sr": [
            "99"
          ],
          "anat": [
            "4"
          ]
        }

    :param auth: XNAT authentication object
    :type auth: :mod:`yaxil.XnatAuth`
    :param label: XNAT MR Session label
    :type label: str
    :param filt: Scan search filter/query
    :type filt: dict
    :param project: XNAT MR Session project
    :type project: str
    :param aid: XNAT Accession ID
    :type aid: str
    :returns: Same dictionary that was passed in, but values are now matching scans
    :rtype: dict
    '''
    if not aid:
        aid = accession(auth, label, project)
    # get scans for accession as a csv
    url = "%s/data/experiments/%s/scans?format=csv" % (auth.url.rstrip('/'), aid)
    logger.debug("issuing http request %s", url)
    r = requests.get(
        url,
        auth=basicauth(auth),
        cookies=auth.cookie,
        verify=CHECK_CERTIFICATE
    )
    if r.status_code != requests.codes.ok:
        raise ScanSearchError(f'response not ok ({r.status_code} {r.reason}) from {r.url}')
    if not r.content:
        raise ScanSearchError("response is empty from %s" % r.url)
    # read the result into a csv reader
    reader = csv.reader(io.StringIO(r.content.decode()))
    columns = next(reader)
    # create an in-memory database
    conn = sqlite3.connect(":memory:")
    c = conn.cursor()
    # create scans table and insert data
    c.execute("CREATE TABLE scans (%s)" % ','.join(columns))
    query = "INSERT INTO scans VALUES (%s)" % ','.join('?' * len(columns))
    for row in reader:
        c.execute(query, [x for x in row])
    conn.commit()
    # run the user supplied filters and return result
    result = col.defaultdict(list)
    for token,filt in iter(filt.items()):
        try:
            result[token] = [x[0] for x in c.execute("SELECT ID FROM scans where %s" % filt)]
        except sqlite3.OperationalError:
            logger.critical("something is wrong with the filter: %s", filt)
            raise
    return result

def history(auth, label=None, project=None, experiment=None):
    if experiment and (label or project):
        raise ValueError('cannot supply experiment with label or project')
    if experiment:
        label,project = experiment.label,experiment.project
    aid = accession(auth, label, project)
    baseurl = auth.url.rstrip('/')
    url = f'{baseurl}/data/experiments/{aid}/history'
    r = requests.get(
        url,
        auth=basicauth(auth),
        cookies=auth.cookie,
        verify=CHECK_CERTIFICATE
    )
    logger.debug(f'response headers {r.headers}')
    if r.status_code != requests.codes.ok:
        message = f'response not ok ({r.status_code} {r.reason}) from {r.url}'
        raise ExperimentHistoryError(message)
    return r.json()

class ExperimentHistoryError(Exception):
    pass

def mrscans(auth, label=None, scan_ids=None, project=None, experiment=None):
    if experiment and (label or project):
        raise ValueError('cannot supply experiment with label or project')
    if experiment:
        label,project = experiment.label,experiment.project
    aid = accession(auth, label, project)
    path = f'/data/experiments/{aid}/scans'
    params = {
        'columns': ','.join(mrscans.columns.keys())
    }
    _,result = _get(auth, path, 'json', autobox=True, params=params)
    for result in result['ResultSet']['Result']:
        if not result['xnat:mrscandata/id']:
            continue
        if scan_ids == None or result['xnat:mrscandata/id'] in scan_ids:
            data = dict()
            for k,v in iter(mrscans.columns.items()):
                data[v] = result[k]
            yield data
mrscans.columns = {
    "ID": "ID",
    "insert_date": "date_archived",
    "insert_user": "archiver",
    "xnat:mrsessiondata/operator": "operator",
    "xnat:mrscandata/id": "id",
    "xnat:mrscandata/quality": "quality",
    "xnat:mrscandata/series_description": "series_description",
    "xnat:mrscandata/scanner": "scanner",
    "xnat:mrscandata/scanner/manufacturer": "scanner_manufacturer",
    "xnat:mrscandata/scanner/model": "scanner_model",
    "xnat:mrscandata/frames": "frames",
    "xnat:mrscandata/note": "note",
    "xnat:mrscandata/type": "type",
    "xnat:mrscandata/parameters/voxelres/x": "vox_x",
    "xnat:mrscandata/parameters/voxelres/y": "vox_y",
    "xnat:mrscandata/parameters/voxelres/z": "vox_z",
    "xnat:mrscandata/parameters/fov/x": "fov_x",
    "xnat:mrscandata/parameters/fov/y": "fov_y",
    "xnat:mrscandata/parameters/tr": "tr",
    "xnat:mrscandata/parameters/te": "te",
    "xnat:mrscandata/parameters/flip": "flip",
    "xnat:mrscandata/parameters/sequence": "sequence",
    "xnat:mrscandata/parameters/imagetype": "image_type",
    "xnat:mrscandata/parameters/scansequence": "scan_sequence",
    "xnat:mrscandata/parameters/seqvariant": "sequence_variant",
    "xnat:mrscandata/parameters/acqtype": "acquisition_type",
    "xnat:mrscandata/parameters/pixelbandwidth": "pix_bandwidth"
}

def srscans(auth, label=None, scan_ids=None, project=None, experiment=None):
    if experiment and (label or project):
        raise ValueError('cannot supply experiment with label or project')
    if experiment:
        label,project = experiment.label,experiment.project
    aid = accession(auth, label, project)
    path = f'/data/experiments/{aid}/scans'
    params = {
        'columns': ','.join(srscans.columns.keys())
    }
    _,result = _get(auth, path, 'json', autobox=True, params=params)
    for result in result['ResultSet']['Result']:
        if not result['xnat:srscandata/id']:
            continue
        if scan_ids == None or result['xnat:srscandata/id'] in scan_ids:
            data = dict()
            for k,v in iter(srscans.columns.items()):
                data[v] = result[k]
            yield data
srscans.columns = {
    "ID": "ID",
    "insert_date": "date_archived",
    "insert_user": "archiver",
    "xnat:imagesessiondata/operator": "operator",
    "xnat:srscandata/id": "id",
    "xnat:srscandata/quality": "quality",
    "xnat:srscandata/note": "note",
    "xnat:srscandata/type": "type",
    "xnat:srscandata/series_description": "series_description",
    "xnat:srscandata/scanner": "scanner",
    "xnat:srscandata/scanner/manufacturer": "scanner_manufacturer",
    "xnat:srscandata/scanner/model": "scanner_model"
}

def scscans(auth, label=None, scan_ids=None, project=None, experiment=None):
    if experiment and (label or project):
        raise ValueError('cannot supply experiment with label or project')
    if experiment:
        label,project = experiment.label,experiment.project
    aid = accession(auth, label, project)
    path = f'/data/experiments/{aid}/scans'
    params = {
        'columns': ','.join(scscans.columns.keys())
    }
    _,result = _get(auth, path, 'json', autobox=True, params=params)
    for result in result['ResultSet']['Result']:
        if not result['xnat:scscandata/id']:
            continue
        if scan_ids == None or result['xnat:scscandata/id'] in scan_ids:
            data = dict()
            for k,v in iter(scscans.columns.items()):
                data[v] = result[k]
            yield data
scscans.columns = {
    "ID": "ID",
    "insert_date": "date_archived",
    "insert_user": "archiver",
    "xnat:imagesessiondata/operator": "operator",
    "xnat:scscandata/id": "id",
    "xnat:scscandata/quality": "quality",
    "xnat:scscandata/note": "note",
    "xnat:scscandata/type": "type",
    "xnat:scscandata/series_description": "series_description",
    "xnat:scscandata/scanner": "scanner",
    "xnat:scscandata/scanner/manufacturer": "scanner_manufacturer",
    "xnat:scscandata/scanner/model": "scanner_model"
}

def odscans(auth, label=None, scan_ids=None, project=None, experiment=None):
    if experiment and (label or project):
        raise ValueError('cannot supply experiment with label or project')
    if experiment:
        label,project = experiment.label,experiment.project
    aid = accession(auth, label, project)
    path = f'/data/experiments/{aid}/scans'
    params = {
        'columns': ','.join(odscans.columns.keys())
    }
    _,result = _get(auth, path, 'json', autobox=True, params=params)
    for result in result['ResultSet']['Result']:
        if not result['xnat:otherdicomscandata/id']:
            continue
        if scan_ids == None or result['xnat:otherdicomscandata/id'] in scan_ids:
            data = dict()
            for k,v in iter(odscans.columns.items()):
                data[v] = result[k]
            yield data
odscans.columns = {
    "ID": "ID",
    "insert_date": "date_archived",
    "insert_user": "archiver",
    "xnat:imagesessiondata/operator": "operator",
    "xnat:otherdicomscandata/id": "id",
    "xnat:otherdicomscandata/quality": "quality",
    "xnat:otherdicomscandata/note": "note",
    "xnat:otherdicomscandata/type": "type",
    "xnat:otherdicomscandata/series_description": "series_description",
    "xnat:otherdicomscandata/scanner": "scanner",
    "xnat:otherdicomscandata/scanner/manufacturer": "scanner_manufacturer",
    "xnat:otherdicomscandata/scanner/model": "scanner_model",
}

def scans(auth, label=None, scan_ids=None, project=None, experiment=None):
    '''
    Get scan information for a MR Session as a sequence of dictionaries

    Example:
        >>> import json
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> for scan in yaxil.scans(auth, 'TestSession01'):
        ...   print(json.dumps(scan, indent=2))
        {
          "ID": "...",
          "date_archived": "...",
          ...
        }
        {
          "ID": "...",
          "date_archived": "...",
          ...
        }
        ...
    '''
    if experiment and (label or project):
        raise ValueError('cannot supply experiment with label or project')
    if experiment:
        label,project = experiment.label,experiment.project
    aid = accession(auth, label, project)
    '''
    Getting experiment details like this may not be necessary if the following 
    issue is fixed https://issues.xnat.org/browse/XNAT-6829
    '''
    experiment_details = __experiment_details(auth, aid)
    '''
    An MR Session can have a mixed scan types (xsi:type) that must be 
    requested separately
    '''
    xsitypes = __get_xsi_types(auth, aid)
    '''
    Call the appropriate handler for each scan type
    '''
    for xsitype in xsitypes:
        if xsitype not in scans.handlers:
            logger.warning('could not find a handler for %s', xsitype)
            continue
        for scan in scans.handlers[xsitype](auth, label, scan_ids, project):
            scan.update(experiment_details)
            yield scan
scans.handlers = {
    'xnat:mrScanData': mrscans,
    'xnat:srScanData': srscans,
    'xnat:scScanData': scscans,
    'xnat:otherDicomScanData': odscans
}

def __get_xsi_types(auth, aid):
    path = f'/data/experiments/{aid}/scans'
    params = {
        'columns': 'xsiType'
    }
    _,result = _get(auth, path, 'json', autobox=True)
    xsitypes = set()
    for result in result['ResultSet']['Result']:
        xsitypes.add(result['xsiType'])
    return xsitypes

def __experiment_details(auth, aid):
  path = f'/data/experiments'
  columns = [
    'URI',
    'xsiType',
    'ID',
    'label',
    'project',
    'subject_ID',
    'subject_label',
    'subject_project',
    'date',
    'time',
    'fieldStrength'
  ]
  params = {
    'ID': aid,
    'columns': ','.join(columns)
  }
  _,result = _get(auth, path, 'json', autobox=True, params=params)
  for result in result['ResultSet']['Result']:
    return {
      'session_uri': result['URI'],
      'xsitype': result['xsiType'],
      'session_id': result['ID'],
      'session_label': result['label'],
      'session_project': result['project'],
      'date_scanned': result['date'],
      'time_scanned': result['time'],
      'subject_id': result['subject_ID'],
      'subject_label': result['subject_label'],
      'subject_project': result['subject_project'],
      'field_strength': result['fieldStrength']
    }

def _get(auth, path, fmt, autobox=True, params=None):
    '''
    Issue a GET request to the XNAT REST API and box the response content.

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :param path: API URL path
    :type path: str
    :param fmt: API result format
    :type fmt: :mod:`yaxil.Format`
    :param autobox: Autobox response content into an appropriate reader or other data structure
    :type autobox: bool
    :param params: Additional query parameters
    :type params: dict
    :returns: Tuple of (URL, :mod:`dict` | :mod:`xml.etree.ElementTree` | :mod:`csv.reader` | :mod:`str`)
    :rtype: tuple
    '''
    if not params:
        params = {}
    url = "%s/%s" % (auth.url.rstrip('/'), path.lstrip('/'))
    params["format"] = fmt
    logger.debug("issuing http request %s", url)
    logger.debug("query parameters %s", params)
    r = requests.get(
        url,
        params=params,
        auth=basicauth(auth),
        cookies=auth.cookie,
        verify=CHECK_CERTIFICATE
    )
    if r.status_code != requests.codes.ok:
        raise RestApiError(f'response not ok ({r.status_code} {r.reason}) from {r.url}')
    if not r.content:
        raise RestApiError("response is empty from %s" % r.url)
    if autobox:
        return r.url,_autobox(r.text, fmt)
    else:
        return r.url,r.content

def get(auth, path, autobox=False, fmt=None, params=None):
    '''
    Make a GET request to XNAT and optionally autobox the 
    response content. Autoboxing will convert the response 
    content to an ``lxml.etree`` object for XML, ``dict`` 
    for JSON, or ``csv.reader`` for CSV.

    Example::
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> path = '/data/config'
        >>> yaxil.get(auth, path).content
        b'...'
    '''
    if not params:
        params = dict()
    urlprefix = auth.url.rstrip('/')
    path = path.lstrip('/')
    url = f'{urlprefix}/{path}'
    if fmt:
        params['format'] = fmt
    logger.debug(f'GET {url}')
    logger.debug(f'query parameters {params}')
    r = requests.get(
        url,
        params=params,
        auth=basicauth(auth),
        cookies=auth.cookie,
        verify=CHECK_CERTIFICATE
    )
    if r.status_code != requests.codes.ok:
        raise RestApiError(f'response not ok ({r.status_code} {r.reason}) from {r.url}')
    if not r.content:
        raise RestApiError(f'response is empty from {r.url}')
    if autobox:
        return Response(url=r.url, content=_autobox(r.text, fmt))
    else:
        return Response(url=r.url, content=r.content)


def _autobox(content, format):
    '''
    Autobox response content.

    :param content: Response content
    :type content: str
    :param format: Format to return
    :type format: `yaxil.Format`
    :returns: Autoboxed content
    :rtype: dict|xml.etree.ElementTree.Element|csvreader
    '''
    if format == Format.JSON:
        return json.loads(content)
    elif format == Format.XML:
        return etree.fromstring(content)
    elif format == Format.CSV:
        try:
            return csv.reader(io.BytesIO(content))
        except TypeError:
            # as per https://docs.python.org/2/library/csv.html#examples
            def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
                # csv.py doesn't do Unicode; encode temporarily as UTF-8:
                csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                                        dialect=dialect, **kwargs)
                for row in csv_reader:
                    # decode UTF-8 back to Unicode, cell by cell:
                    yield [unicode(cell, 'utf-8') for cell in row]
            def utf_8_encoder(unicode_csv_data):
                for line in unicode_csv_data:
                    yield line.encode('utf-8')
            return unicode_csv_reader(io.StringIO(content))
    else:
        raise AutoboxError("unknown autobox format %s" % format)

def exists(auth, xnatid, datatype='experiments'):
    '''
    Test if an object exists

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :param xnatid: XNAT object ID
    :param xnatid: str
    :param datatype: XNAT data type
    :type datatype: str
    :returns: True or False
    :rtype: bool
    '''
    url = '{0}/data/{1}/{2}'.format(auth.url.rstrip('/'), datatype, xnatid)
    logger.debug('issuing http request %s', url)
    r = requests.get(
        url,
        auth=basicauth(auth),
        cookies=auth.cookie,
        verify=CHECK_CERTIFICATE
    )
    if r.status_code == requests.codes.ok:
        return True
    return False

def has(auth, xsitype, project=None):
    '''
    Test if a project contains any items of a particular xsi:type.

    Example:
        >>> import yaxil
        >>> auth = yaxil.auth('doctest')
        >>> yaxil.has(auth, 'neuroinfo:anatqc', project='TestProject01')
        True

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :param xsitype: XNAT xsi:type
    :param xsitype: str
    :param project: XNAT Project
    :type project: str
    :returns: True or False
    :rtype: bool
    '''
    path = "/data/experiments"
    params = {
        "xsiType": xsitype,
        "columns": 'ID'
    }
    if project:
        params["project"] = project
    url,result = _get(auth, path, Format.JSON, autobox=True, params=params)
    try:
        __quick_validate(result)
    except ResultSetError as e:
        raise ResultSetError("%s in response from %s" % (e.message, url))
    if int(result["ResultSet"]["totalRecords"]) == 0:
        return False
    return True

def storexar_cli(auth, archive):
    '''
    StoreXAR through command line utility

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :param path: Filesystem location of ZIP (XAR) archive
    :type path: str
    '''
    StoreXAR = commons.which('StoreXAR')
    if not StoreXAR:
        raise CommandNotFoundError('StoreXAR not found')
    archive = os.path.abspath(archive)
    popd = os.getcwd()
    os.chdir(os.path.dirname(StoreXAR))
    cmd = [
        'sh',
        'StoreXAR',
        '-host', auth.url,
        '-u', auth.username,
        '-p', auth.password,
        '-f', archive
    ]
    try:
        logger.debug(cmd)
        output = sp.check_output(cmd, stderr=sp.PIPE).decode()
        if 'Upload Completed' in output:
            logger.info('XAR upload complete')
    except sp.CalledProcessError as e:
        logger.error(e.stdout)
        logger.error(e.stderr)
        raise e
    os.chdir(popd)

def storerest(auth, artifacts_dir, resource_name):
    '''
    Store data into XNAT over REST API

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :param artifacts_dir: Filesystem location of assessor artifacts
    :type artifacts_dir: str
    :param resource_name: Resource name
    :type resource_name: str
    '''
    assessment = os.path.join(artifacts_dir, 'assessor', 'assessment.xml')
    resources = os.path.join(artifacts_dir, 'resources')

    # parse assessor and session ID from assessment.xml
    with open(assessment) as fo:
        root = etree.parse(fo)
    aid = root.find('.').attrib['ID']
    sid = root.findall('.//{http://nrg.wustl.edu/xnat}imageSession_ID').pop().text
    logger.debug(f'assessor id={aid}')
    logger.debug(f'session id={sid}')

    baseurl = auth.url.rstrip('/')
    
    # create (post) new image assessor
    url = f'{baseurl}/data/experiments/{sid}/assessors'
    logger.debug(f'posting {assessment} to {url}')
    r = requests.post(
        url,
        auth=basicauth(auth),
        cookies=auth.cookie,
        files={
            'file': open(assessment, 'rb')
        },
        allow_redirects=True,
        verify=CHECK_CERTIFICATE
    )
    if r.status_code == requests.codes.ok:
        logger.debug(f'assessment {aid} uploaded successfully')
    elif r.status_code == requests.codes.conflict:
        logger.debug(f'assessment {aid} likely already exists')
        return
    else:
       raise StoreRESTError(f'assessment {assessment} failed to upload ({r.status_code})')

    # create (put) new image assessor resource folder
    url = f'{baseurl}/data/experiments/{sid}/assessors/{aid}/resources/{resource_name}'
    logger.debug('PUT %s', url)
    r = requests.put(
        url,
        auth=basicauth(auth),
        cookies=auth.cookie,
        allow_redirects=True,
        verify=CHECK_CERTIFICATE
    )
    if r.status_code == requests.codes.ok:
        logger.debug(f'resource folder created {resource_name}')
    elif r.status_code == requests.codes.conflict:
        logger.debug(f'resource folder {resource_name} likely already exists')
    else:
       raise StoreRESTError(f'could not create resource folder {resource_name} ({r.status_code})')

    # upload (put) image assessor resource files
    for resource in os.listdir(resources):
      resource_dir = os.path.join(resources, resource)
      for f in os.listdir(resource_dir):
        fullfile = os.path.join(resource_dir, f)
        url = f'{baseurl}/data/experiments/{sid}/assessors/{aid}/resources/{resource_name}/files/{resource}/{f}'
        logger.debug('PUT %s', url)
        r = requests.put(
          url,
          auth=basicauth(auth),
          cookies=auth.cookie,
          files={
            'file': open(fullfile, 'rb')
          },
          allow_redirects=True,
          verify=CHECK_CERTIFICATE
        )
        if r.status_code == requests.codes.ok:
            logger.debug(f'file {fullfile} was stored successfully as {resource}')
        elif r.status_code == requests.codes.conflict:
            logger.debug(f'resource {resource} likely already exists')
        else:
            raise StoreRESTError(f'could not store resource file {fullfile} ({r.status_code})')

class StoreRESTError(Exception):
    pass

def storexar(auth, archive, verify=True):
    '''
    StoreXAR implementation

    :param auth: XNAT authentication
    :type auth: :mod:`yaxil.XnatAuth`
    :param path: Filesystem location of ZIP (XAR) archive
    :type path: str
    '''
    # soap envelope
    envelope = '''<?xml version="1.0" encoding="UTF-8"?>
                  <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                                    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                    <soapenv:Body>
                      <execute soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" />
                    </soapenv:Body>
                  </soapenv:Envelope>'''

    with requests.Session() as s:
        # determine whether URL will be redirected
        redir_url = requests.head(auth.url, allow_redirects=True, verify=verify).url

        # create axis session
        logger.debug('creating soap service session')
        url = redir_url.rstrip('/') + '/axis/CreateServiceSession.jws'
        r = s.post(
            url,
            data=envelope,
            headers={
                'User-Agent': 'Axis/1.3',
                'SOAPAction': '""'
            },
            auth=basicauth(auth),
            verify=verify
        )

        if r.history:
          for i,resp in enumerate(r.history):
            logger.debug('SOAP service redirect #%i: %s to %s', i, resp.status_code, resp.url)

        logger.debug('SOAP service session url: %s', r.url)
        logger.debug('SOAP service session status: %s', r.status_code)
        logger.debug('SOAP service session body: %s', r.text)
        logger.debug('SOAP service session headers: \n%s', r.headers)

        logger.debug('Session cookies: \n%s', requests.utils.dict_from_cookiejar(s.cookies))

        if r.status_code != requests.codes.ok:
            raise StoreXARError(f'response not ok ({r.status_code} {r.reason}) from {r.url}')

        # post the xar archive
        logger.debug('posting xar archive')
        url = redir_url.rstrip('/') + '/app/template/StoreXAR.vm'
        r = s.post(
            url,
            verify=verify,
            files={
                'archive': (archive, open(archive, 'rb'), 'application/octet-stream', {})
            }
        )

        if r.history:
          for i,resp in enumerate(r.history):
            logger.debug('XAR archive upload redirect #%i: %s to %s', i, resp.status_code, resp.url)

        logger.debug('XAR archive upload url: %s', r.url)
        logger.debug('XAR archive upload status: %s', r.status_code)
        logger.debug('XAR archive upload body: %s', r.text)
        logger.debug('XAR archive upload headers: \n%s', r.headers)

        if r.status_code != requests.codes.ok:
            raise StoreXARError(f'response not ok ({r.status_code} {r.reason}) from {r.url}')

        # check for success string in response content
        if not 'Upload Complete' in r.text:
            raise StoreXARError('response text from %s is\n%s' % (r.url, r.text))
        logger.debug('upload complete')

class StoreXARError(Exception):
    pass

if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE)
