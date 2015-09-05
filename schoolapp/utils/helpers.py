__author__ = 'ashish'
from utils import log
from django.core.cache import cache
import time, json
logging = log.Logger.get_logger(__file__)

def authenticate_user():
    """
    this will be called when the user has to be authenticated

    """
    pass

class QueueRequests():

    @staticmethod
    def enqueue(tag, data):
        data['ts'] = int(time.time())
        logging.debug('[QueueRequests] ' + tag)
        if tag is not None:
            cache.lpush('queue::' + tag, json.dumps(data))
        else:
            logging.error('invalid queue request')