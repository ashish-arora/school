#!/usr/bin/env python

# Copyright 2014 Gregor Uhlenheuer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import argparse
import json
import logging
import os
import struct
import sys
import urllib2
from django.core.management.base import BaseCommand
from schoolapp.models import User
import base64
import bson


#
# DEFAULTS AND CONSTANTS
#

DEFAULT_LOG_DIR = '/var/log/ejabberd'
FALLBACK_URL = 'http://localhost:8000/auth/'
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json' }


#
# CLASS DEFINITIONS
#

class EjabberdError(Exception):
    '''Exception class that holds ejabberd related errors.'''

    def __init__(self, ex):
        self.ex = ex

    def __str__(self):
        return repr(self.ex)

class ApiHandler:
    '''
    Class to execute HTTP requests to process
    the authentication orders from ejabberd.
    '''

    def __init__(self, url, headers):
        '''Initialize an ApiHandler instance.'''

        self.url = url
        self.headers = headers

    def call(self, call, data):
        '''
        Call the specified authentication API using the
        urllib2 library functions.
        '''

        url = '%s/%s' % (self.url, call)
        req = urllib2.Request(url, data, self.headers)
        res = urllib2.urlopen(req)

        return json.load(res)

class EjabberdAuth:
    '''
    Class that encapsulates the ejabberd authentication logic.
    '''

    def __init__(self, url, headers, handler=None):
        '''
        Initialize a new EjabberdAuth instance.
        '''
        self.url = url
        self.headers = headers

        if handler is None:
            self.handler = ApiHandler(url, headers)
        else:
            self.handler = handler

    @staticmethod
    def make_jid(user, host):
        '''Build a JID using the given user and host'''

        return '%s@%s' % (user, host)

    def __from_ejabberd(self):
        '''
        Listen on stdin and read input data sent from the
        connected ejabberd instance.
        '''

        try:
            input_length = sys.stdin.read(2)

            if len(input_length) is not 2:
                logging.warn('ejabberd called with invalid input')
                return None

            (size,) = struct.unpack('>h', input_length)
            result = sys.stdin.read(size)

            logging.info('Read %d bytes: %s', size, result)

            return result.split(':')
        except IOError:
            raise EjabberdError('Failed to read from ejabberd via stdin')

    def __to_ejabberd(self, success):
        '''
        Convert the input data into an ejabberd compatible
        format and send it to stdout.
        '''

        answer = 1 if success else 0
        token = struct.pack('>hh', 2, answer)

        sys.stdout.write(token)
        sys.stdout.flush()

        logging.info('Returned %s success', 'with' if success else 'without')

    def __call_api(self, call, data):
        '''
        Call the JSON compatible API handler with the specified data
        and parse the response for a success.
        '''

        '''body = json.dumps(data)
        result = self.handler.call(call, body)

        success = result['success']

        if not success:
            msg = result['message']
            logging.warn('Call to API returned without success: ' + msg)
        '''
        return 1

    def __auth(self, username, server, token):
        '''Try to authenticate the user with the specified password.'''

        logging.error('Processing "auth"')
        return True
        #jid = EjabberdAuth.make_jid(username, server)
        try:
            user = User.objects.get(id=username, token=token)
            logging.debug('Found jabber id' + str(username))
            return True
        except User.DoesNotExist:
            logging.error(username + ' is not a valid user')
        except Exception, ex:
            logging.error('Unhandled error: ' + str(ex))
        return False

    def __isuser(self, username, server):
        '''Try to find the specified user.'''

        logging.debug('Processing "isuser"')

        jid = EjabberdAuth.make_jid(username, server)
        data = {'username': jid}
        try:
            user = User.objects.get(id=username)
            logging.debug('Found user with jabber id ' + str(user.jabber_id))
            return True
        except User.DoesNotExist:
            logging.debug('No jabber id ' + str(jid))
            return False
        except Exception, ex:
            logging.debug('Unhandled error: ' + str(ex))
            return False

        #return self.__call_api('exists', data)

    def __setpass(self, username, server, token):
        '''Try to set the user's password.'''

        logging.debug('Processing "setpass"')
        try:
            user = User.objects.get(id=username)
            user.token = token
            user.save()
            return True
        except User.DoesNotExist:
            logging.error('No jabber id ' + str(username))
            return False
        except Exception, ex:
            logging.debug('Unhandled error: ' + str(ex))
            return False

    def loop(self):
        '''
        Start the endless loop that reads on stdin and passes
        the authentication results to stdout towards the
        connected ejabberd instance.
        '''
        while True:
            try:
                data = self.__from_ejabberd()
            except KeyboardInterrupt:
                logging.info('Terminating by user input')
                break
            except EjabberdError, err:
                logging.warn('Input error: ' + err)
                break

            success = False
            logging.info("data is :%s" % data)
            cmd = data[0]

            logging.info("data: %s" % data)

            if cmd == 'auth':
                success = self.__auth(data[1], data[2], data[3])
            elif cmd == 'isuser':
                success = self.__isuser(data[1], data[2])
            elif cmd == 'setpass':
                success = self.__setpass(data[1], data[2], data[3])
            else:
                logging.warn('Unhandled ejabberd cmd "%s"', cmd)

            self.__to_ejabberd(success)


def get_args():
    '''
    Parse some basic configuration from command line arguments.
    '''

    # build command line argument parser
    desc = 'ejabberd authentication script'
    parser = argparse.ArgumentParser(description=desc)

    # base url
    parser.add_argument('url',
            nargs='?',
            metavar='URL',
            default=FALLBACK_URL,
            help='base URL (default: %(default)s)')

    # log file location
    parser.add_argument('-l', '--log',
            default=DEFAULT_LOG_DIR,
            help='log directory (default: %(default)s)')

    # debug log level
    parser.add_argument('-d', '--debug',
            action='store_const', const=True,
            help='toggle debug mode')

    args = vars(parser.parse_args())

    return args['url'], args['debug'], args['log']


"""if __name__ == '__main__':
    URL, DEBUG, LOG = get_args()

    LOGFILE = LOG + '/kauth.log'
    LEVEL = logging.DEBUG if DEBUG else logging.INFO
    PID = str(os.getpid())
    FMT = '[%(asctime)s] ['+PID+'] [%(levelname)s] %(message)s'

    # redirect stderr
    ERRFILE = LOGFILE
    sys.stderr = open(ERRFILE, 'a+')

    # configure logging
    logging.basicConfig(level=LEVEL, format=FMT, filename=LOGFILE)

    logging.info('Starting ejabberd auth script')
    logging.info('Using %s as base URL', URL)
    logging.info('Running in %s mode', 'debug' if DEBUG else 'release')

    EJABBERD = EjabberdAuth(URL, HEADERS)
    EJABBERD.loop()

    logging.warn('Terminating ejabberd auth script')

"""

class Command(BaseCommand):
    help = "Runs an ejabberd auth service"

    def handle(self, **options):
        print "inside handle"
        URL, DEBUG, LOG = get_args()
        LOGFILE = LOG + '/kauth.log'
        LEVEL = logging.DEBUG if DEBUG else logging.DEBUG
        PID = str(os.getpid())
        FMT = '[%(asctime)s] ['+PID+'] [%(levelname)s] %(message)s'

        # redirect stderr
        ERRFILE = LOGFILE
        sys.stderr = open(ERRFILE, 'a+')

        # configure logging
        logging.basicConfig(level=LEVEL, format=FMT, filename=LOGFILE)

        logging.info('Starting ejabberd auth script')
        logging.info('Using %s as base URL', URL)
        logging.info('Running in %s mode', 'debug' if DEBUG else 'release')

        EJABBERD = EjabberdAuth(URL, HEADERS)
        EJABBERD.loop()


# vim: set et sw=4 sts=4 tw=80:
