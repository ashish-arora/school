__author__ = 'ashish'

from django.core.management.base import BaseCommand
from schoolapp.utils import log
from django.core.cache import cache

logging = log.Logger.get_logger(__file__)

class Command(BaseCommand):
    help = "handled login and logout event in ejabberd"

    def handle(self, *args, **options):
        try:
            logging.debug('Handle starting')
            is_logged_in = args[0]
            jabber_id = args[1]
            resource = args[2]
            logging.debug('Jabber Id got :%s with resource : %s'%(jabber_id, resource))
            if int(is_logged_in):
                if jabber_id and resource:
                    cache.set(str(jabber_id) + ':' + str(resource))
                    logging.debug("Key has been set: %s" % (str(jabber_id) + ':' + str(resource)))
                else:
                    logging.debug("Arguments are not valid for setting the user cache")
            else:
                if jabber_id and resource:
                    cache.delete(str(jabber_id) + ':' + str(resource))
                    logging.debug("Deleted the key: %s" % (str(jabber_id) + ':' + str(resource)))
                else:
                    logging.debug("Arguments are not valid for setting the user cache")
        except Exception, ex:
            logging.error("Error while executing login logout event: " + str(ex))
        except KeyboardInterrupt:
            logging.error("Received Keyboard Interrupt")
            raise SystemExit(0)