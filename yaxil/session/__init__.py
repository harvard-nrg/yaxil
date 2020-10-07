import yaxil

class Session(object):
    def __init__(self, auth):
        self._auth = auth
        self.url = auth.url
        self.username = auth.username

    def accession(self, *args, **kwargs):
        return yaxil.accession(self._auth, *args, **kwargs)

    def subjects(self, *args, **kwargs):
        return yaxil.subjects(self._auth, *args, **kwargs)

    def experiments(self, *args, **kwargs):
        return yaxil.experiments(self._auth, *args, **kwargs)

    def extendedboldqc(self, *args, **kwargs):
        return yaxil.extendedboldqc(self._auth, *args, **kwargs)

    def download(self, *args, **kwargs):
        return yaxil.download(self._auth, *args, **kwargs)

    def scans(self, *args, **kwargs):
        return yaxil.scans(self._auth, *args, **kwargs)

    def scansearch(self, *args, **kwargs):
        return yaxil.scansearch(self._auth, *args, **kwargs)

    def exists(self, *args, **kwargs):
        return yaxil.exists(self._auth, *args, **kwargs)

    def has(self, *args, **kwargs):
        return yaxil.has(self._auth, *args, **kwargs)

    def storexar(self, *args, **kwargs):
        return yaxil.storexar(self._auth, *args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return
