__author__ = 'ashish'
from schoolapp.utils import log
from django.core.cache import cache
import time, json
logging = log.Logger.get_logger(__file__)
from schoolapp.models import User
from mongoengine.errors import *

def authenticate_user(func):
    """
    this will be called when the user has to be authenticated

    """
    def inner(self, request):
        username = self.request.data.get("username", None)
        password = self.request.data.get("password", None)
        try:
            user = User.objects.get(username=username, password=password)
        except DoesNotExist:
            raise ValidationError("User does not exist")
        else:
            request.user = user
            return func(self, request)
    return inner

class QueueRequests():

    @staticmethod
    def enqueue(tag, data):
        data['ts'] = int(time.time())
        logging.debug('[QueueRequests] ' + tag)
        if tag is not None:
            cache.lpush('queue::' + tag, json.dumps(data))
        else:
            logging.error('invalid queue request')