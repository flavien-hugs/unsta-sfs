import json
from enum import StrEnum


class SortEnum(StrEnum):
    ASC = "asc"
    DESC = "desc"


BUCKET_POLICY_CONFIG = {
    "Version": "2012-10-17",
    "Statement": [
        {"Sid": "AllowAllObjects", "Effect": "Allow", "Principal": "*", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::*/*"}
    ],
}

policy_document = json.dumps(BUCKET_POLICY_CONFIG)
