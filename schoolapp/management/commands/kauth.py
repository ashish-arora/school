import sys, os
import struct
from django.core.management.base import BaseCommand
import logging
from datetime import datetime
from django.conf import settings
from schoolapp.models import User
import base64
import bson

settings.DEBUG = False

class Command(BaseCommand):
    help = "Runs an ejabberd auth service"

    def __init__(self, *args, **kwargs):
        """
            Creation of the ejabberd atuh bridge service.
            :Parameters:
                - `args`: all non-keyword arguments
                - `kwargs`: all keyword arguments
        """
        BaseCommand.__init__(self, *args, **kwargs)
        try:
            log_level = int(logging.DEBUG)
        except:
            log_level = logging.INFO
        if os.access("/var/log/ejabberd/kauth.log", os.W_OK):
            logging.basicConfig(
                                level=log_level,
                                format='%(asctime)s %(levelname)s %(message)s',
                                filename="/var/log/ejabberd/kauth.log",
                                filemode='a')
        else:
            logging.basicConfig(
                                level=log_level,
                                format='%(asctime)s %(levelname)s %(message)s',
                                stream=sys.stderr)
            logging.warn(('Could not write to ' +
                          '/var/log/ejabberd/kauth.log' +
                          '. Falling back to stderr ...'))
        logging.info(('ejabberd kauth process started' +' (more than one is common)'))

    def _generate_response(self, success=False):
        """
        Creates and sends a response back to the ejabberd server.

        :Parameters
           - `success`: boolean if we should respond successful or not
        """
        logging.debug('Generating a response ...')
        result = 0
        if success:
            result = 1
        logging.debug('Sending response of ' + str(result))
        sys.stdout.write(struct.pack('>hh', 2, result))
        sys.stdout.flush()
        logging.debug('Response of ' + str(result) + ' sent')

    def _handle_isuser(self, jid):
        """
        Handles the isuer ejabberd command.

        :Parameters:
           - `username`: the user name to verify exists
        """
        try:
            user = User.objects.get(id=jid)
            logging.debug('Found user with jabber id ' + str(user.jabber_id))
            self._generate_response(True)
        except User.DoesNotExist:
            logging.debug('No jabber id ' + str(jid))
            self._generate_response(False)
        except Exception, ex:
            logging.debug('Unhandled error: ' + str(ex))

    def _handle_auth(self, jid, token):
        """
        Handles authentication of the user.

        :Parameters:
           - `username`: the username to verify
           - `password`: the password to verify with the user
        """
        logging.info('Starting auth check')
        try:
            user = User.objects.get(id=jid, token=token)
            logging.debug('Found jabber id and logged in' + str(jid))
            self._generate_response(True)
            """
            if not user.is_login:
                try:
                    user.is_login = True
                    user.save()
                except Exception, ex:
                    logging.warn("Could not save user logged in:" + str(ex))
                logging.debug('Updated ' + jid + ' logged in status')
            """
        except User.DoesNotExist:
            logging.info(jid + ' is not a valid user')
            self._generate_response(False)
        except Exception, ex:
            logging.fatal('Unhandled error: ' + str(ex))

    def handle(self, **options):
        """
        How to check if a user is valid

        :Parameters:
           - `options`: keyword arguments
        """
        try:
            while True:
                logging.info("started")
                try:
                    length = sys.stdin.read(2)
                    size = struct.unpack('>h', length)[0]
                    input_recv = sys.stdin.read(size).split(':')
                    operation = input_recv.pop(0)
                except Exception, ex:
                    logging.error("Data was not in the right format: " + str(ex))
                    self._generate_response(False)
                    continue
                logging.info("Got input as %s with input %s" %(operation, input_recv[0]))
                try:
                    _id = bson.ObjectId(base64.b64decode(input_recv[0]))
                except Exception, ex:
                    logging.error("Error occurred :%s" %str(ex))
                    self._generate_response(False)
                    continue
                if operation == 'auth':
                    logging.info("inside auth operation")
                    self._handle_auth(_id, input_recv[2])
                elif operation == 'isuser':
                    self._handle_isuser(_id)
                elif operation == 'setpass':
                    self._generate_repsonse(False)
                else:
                    logging.warn('Operation "' + operation + '" unknown!')
        except KeyboardInterrupt:
            logging.debug("Received Keyboard Interrupt")
            raise SystemExit(0)
    def __del__(self):
        logging.info("Shutting down kauth.")
