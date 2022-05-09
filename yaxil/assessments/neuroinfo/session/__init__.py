import yaxil.assessments.neuroinfo as neuroinfo

class Session:
    def __init__(self, auth):
        self._auth = auth
    def boldqc(self, *args, **kwargs):
        return neuroinfo.boldqc(self._auth, *args, **kwargs)
    def anatqc(self, *args, **kwargs):
        return neuroinfo.anatqc(self._auth, *args, **kwargs)
    def t2qc(self, *args, **kwargs):
        return neuroinfo.t2qc(self._auth, *args, **kwargs)
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        return
