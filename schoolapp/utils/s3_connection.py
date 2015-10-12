__author__ = 'ashish'

"""
`boto` internally handles pooling of S3 connections
"""

import boto
from school.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


class S3Connection(object):
    instance = None

    @classmethod
    def get_instance(cls):
        if not cls.instance:
            cls.instance = boto.connect_s3(
                AWS_ACCESS_KEY_ID,
                AWS_SECRET_ACCESS_KEY
            )
        return cls.instance
