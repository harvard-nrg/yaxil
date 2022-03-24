import yaxil

def getfile(auth, file):
    return yaxil.download(auth, file['URI'])
