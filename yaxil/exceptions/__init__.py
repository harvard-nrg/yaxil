class YaxilError(Exception):
    pass

class AuthError(YaxilError):
    pass

class MultipleAccessionError(YaxilError):
    pass

class NoAccessionError(YaxilError):
    pass

class NoExperimentsError(YaxilError):
    pass

class NoSubjectsError(YaxilError):
    pass

class AccessionError(YaxilError):
    pass

class DownloadError(YaxilError):
    pass

class ResultSetError(YaxilError):
    pass

class ScanSearchError(YaxilError):
    pass

class EQCNotFoundError(YaxilError):
    pass

class RestApiError(YaxilError):
    pass

class AutoboxError(YaxilError):
    pass

