import yaxil

class Session(object):
    def __init__(self, auth):
        self._auth = auth

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

    def storexar(self, *args, **kwargs):
        return yaxil.storexar(self._auth, *args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return
