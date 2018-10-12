import yaxil

class Session(object):
    def __init__(self, auth):
        self._auth = auth

    def accession(self, *args, **kwargs):
        return yaxil.accession(self._auth, *args, **kwargs)

    def subject(self, *args, **kwargs):
        return yaxil.subject(self._auth, *args, **kwargs)

    def experiment(self, *args, **kwargs):
        return yaxil.experiment(self._auth, *args, **kwargs)

    def extendedboldqc(self, *args, **kwargs):
        return yaxil.extendedboldqc(self._auth, *args, **kwargs)

    def download(self, *args, **kwargs):
        return yaxil.download(self._auth, *args, **kwargs)

    def scans(self, *args, **kwargs):
        return yaxil.scans(self._auth, *args, **kwargs)

    def scansearch(self, *args, **kwargs):
        return yaxil.scansearch(self._auth, *args, **kwargs)
