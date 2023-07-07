import yaxil
import yaxil.assessments.neuroinfo as neuroinfo

class Session:
    def __init__(self, auth):
        self._auth = auth
        self.url = auth.url
        self.username = auth.username

    def boldqc(self, *args, **kwargs):
        return neuroinfo.boldqc(self._auth, *args, **kwargs)

    def anatqc(self, *args, **kwargs):
        return neuroinfo.anatqc(self._auth, *args, **kwargs)

    def t2qc(self, *args, **kwargs):
        return neuroinfo.t2qc(self._auth, *args, **kwargs)

    def dwiqc(self, *args, **kwargs):
        return neuroinfo.dwiqc(self._auth, *args, **kwargs)

    def __enter__(self):
        self._auth = yaxil.start_session(self._auth)
        return self

    def __exit__(self, type, value, traceback):
        yaxil.end_session(self._auth)
        return
