from enum import StrEnum


class SfsErrorCodes(StrEnum):
    SFS_INVALID_KEY = "sfs/invalid-key"
    SFS_INVALID_TAGS_FORMAT = "sfs/invalid-tags-format"
    SFS_INVALID_DATA = "sfs/invalid-data"
    SFS_INVALID_NAME = "sfs/invalid-name"
    SFS_INVALID_FILE = "sfs/invalid-file"
    SFS_ACCESS_DENIED = "sfs/access-denied"
    SFS_UNKNOWN_ERROR = "sfs/unknown-error"
    SFS_INVALID_RESOURCE = "sfs/invalid-resource"
    SFS_BUCKET_NOT_FOUND = "sfs/bucket-not-found"
    INTERNAL_SERVER_ERROR = "app/internal-server-error"
    REQUEST_VALIDATION_ERROR = "app/request-validation-error"
    SFS_BUCKET_NAME_ALREADY_EXIST = "sfs/bucket-name-alreay-exist"
    AUTH_ACCESS_DENIED = "app/service-access-denied"
    SFS_FILE_NOT_FOUND = "sfs/file-not-found"
