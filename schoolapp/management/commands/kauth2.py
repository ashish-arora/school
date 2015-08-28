__author__ = 'ashish'
#!/usr/bin/python

import sys, os, fcntl
from struct import *
from subprocess import *

# auth_script = "/path/to/real/auth/script"
auth_script = "/Users/ashish/school/schoolapp/management/commands/kauth.py"

def from_ejabberd():
    input_length = sys.stdin.read(2)
    (size,) = unpack('>h', input_length)
    return sys.stdin.read(size)

def to_ejabberd(answer):
    token = pack('>hh', 2, answer)
    sys.stdout.write(token)
    sys.stdout.flush()


child = Popen([auth_script], stdin=PIPE, stdout=PIPE)
childout = child.stdout.fileno()
fcntl.fcntl(childout, fcntl.F_SETFL, os.O_NONBLOCK)
log = open("/var/log/ejabberd/kauth.log",'a+b',0)

while True:
    request = from_ejabberd()
    size = pack('>h', len(request))
    child.stdin.write(size)
    child.stdin.write(request)
    child.stdin.flush()

    log.write("Request: ")
    log.write(request)
    log.write('\n')

    result = 0
    response_start = ""
    while response_start == "":
        try:
            response_start = os.read(childout, 2)
        except OSError, err:
            pass
    (size,) = unpack('>h', response_start)
    log.write("Response: ")
    if size == 2:
        response_rest = os.read(childout, 2)
        (result,) = unpack('>h', response_rest)
        log.write( "%d" % result )
    else:
        done = False
        log.write(response_start)
        response_rest = ""
        while not done:
            try:
                char = os.read(childout, 1)
                response_rest += char
            except OSError, err:
                done = True
        log.write(response_rest)

    log.write('\n')
    log.flush()
    to_ejabberd(result)
