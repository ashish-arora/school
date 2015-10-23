__author__ = 'ashish'
#!/usr/bin/env python
from schoolapp.utils import log
from redis.exceptions import TimeoutError
import time
import sys
import signal
import json
import socket
import gevent
from gevent import monkey, greenlet
from school.settings import ATTENDANCE_NOTIFICATION_QUEUE, HOMEWORK_NOTIFICATION_QUEUE, GCM_APIKEY,GCM_PROJECT_ID,GCM_QUEUE,SMS_QUEUE,smsgw_ssd_url,ssd_auth_key,ssd_sender_id
from schoolapp.utils.jabber_client import JabberClient
from gcm.gcm import GCM
from models import CustomUser
import requests
from school.settings import REDIS_CONN as cache
from school.settings import STATUS_UPDATE_QUEUE
monkey.patch_all()

logging = log.Logger.get_logger(__file__)

TIME_OUT = 5
INTERVAL = 1
handlers = []

def shutdown(signum, frame):
    logging.error('received signal to stop')
    for handler in handlers:
        handler.stop()
    logging.error('stopped all listeners')
    sys.exit(1)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

class QueueProcessor():
    @staticmethod
    def process(queue, data):
        if queue == ATTENDANCE_NOTIFICATION_QUEUE:
            AttendanceNotification.perform(data)
        elif queue == GCM_QUEUE:
            GcmPush.perform(data)
        else:
            logging.error('invalid request: ' + queue + '   ' + data)

class QueueHandler(greenlet.Greenlet):
    def __init__(self, tid, queue, qid):
        greenlet.Greenlet.__init__(self)
        self.tid = tid
        self.queue = queue
        self.qid = qid
        self.running = True
        self.machine_name = socket.gethostname()

    def run(self):
        queue = self.queue
        id = str(self.qid)
        logging.error('checking: ' + queue + '  ' + id)

        source_queue = 'queue::' + queue
        temp_queue = 'temp::' + self.machine_name + "::" + id + "::" + source_queue

        #To process a request which might not be done due to restart
        obj = cache.lindex(temp_queue, 0)
        if obj is not None:
            logging.error("Processing previous entry temp_queue=%s qid=%s", temp_queue, str(self.qid))
            try:
                QueueProcessor.process(queue, obj)
            except Exception as e:
                logging.exception("error while processing previous entry: %s. Reason: %s", obj, e.message)
                self.enqueue_in_error_queue(source_queue, id, obj)
            cache.lpop(temp_queue)

        while self.running:
            obj = None
            try:
                obj = cache.brpoplpush(source_queue, temp_queue, TIME_OUT)
            except TimeoutError:
                gevent.sleep(INTERVAL)
            except Exception as e:
                logging.exception('unable to fetch object from redis. Reason: ' + e.message)
                gevent.sleep(INTERVAL)
            if obj is not None:
                try:
                    QueueProcessor.process(queue, obj)
                except Exception as e:
                    logging.exception("error while processing: %s. Reason: %s", obj, e.message)
                    self.enqueue_in_error_queue(source_queue, id, obj)
                cache.lpop(temp_queue)
            else:
                logging.error("[%s] No entry to process. Sleeping", self.queue)
                gevent.sleep(INTERVAL)
            gevent.sleep(0)

    def enqueue_in_error_queue(self, source_queue, thread_id, data):
        try:
            error_queue = 'error' + "::" + source_queue
            error_queue_data = dict(data=data, host=self.machine_name, id=thread_id, ts= int(time.time()))
            cache.lpush(error_queue, json.dumps(error_queue_data))
        except Exception as e:
            logging.exception("error while enqueue in error queue: %s thread_id: %s data: %s  Reason: %s", source_queue, thread_id, data, e.message)

    def stop(self):
        self.running = False
        logging.error('stopped tid: ' + str(self.tid) + '  queue: ' + self.queue + '  qid: ' + str(self.qid))

class AttendanceNotification(object):
    queue = ATTENDANCE_NOTIFICATION_QUEUE

    @staticmethod
    def compose_message(name, is_present):
        if is_present:
            return "Your child %s is present today" % name
        else:
            return "Your child %s is absent today" % name

    @staticmethod
    def perform(data):
        parent_msisdn = data.get('msisdn')
        student_name = data.get('name')
        is_present=int(data.get('is_present'))
        message = AttendanceNotification.compose_message(student_name, is_present)
        GcmPush.perform({"msisdn": parent_msisdn, "message": message})
        logging.debug("Message has been sent to parent number: %s" % parent_msisdn)


class HomeWorkNotification(object):
    queue = HOMEWORK_NOTIFICATION_QUEUE

    @staticmethod
    def compose_message(name, subject_name, homework):
        return "%s homework: %s" %(subject_name, homework)

    @staticmethod
    def perform(data):
        parent_msisdn = data.get('msisdn')
        student_name = data.get('name')
        subject_name = data.get('subject_name')
        homework= data.get('homework')
        message = HomeWorkNotification.compose_message(student_name, subject_name, homework)
        GcmPush.perform({"msisdn": parent_msisdn, "message": message})
        logging.debug("Homework has been sent to parent number: %s" % parent_msisdn)

class GcmPush(object):
    queue = GCM_QUEUE
    # Plaintext request
    @staticmethod
    def perform(data):
        gcm = GCM(GCM_APIKEY)
        msisdn = data.get('msisdn')
        user = None
        try:
            user=CustomUser.objects.get(msisdn)
        except Exception as e:
            logging.exception("GCM push send failed to this msisdn : %s", msisdn)
            return
        if(user.devices and len(user.devices) > 0):
            devices = user.devices
        reg_id = devices.get('dev_token', None)
        if reg_id and data['message']:
            gcm.plaintext_request(registration_id=reg_id, data=data['message'])

class SendSms(object):
    queue = SMS_QUEUE

    @staticmethod
    def perform(data):
        msisdn = data.get('msisdn')
        message = data.get('message')
        #http://sms.ssdindia.com/api/sendhttp.php?authkey=YourAuthKey&mobiles=919999999990,919999999999&message=message&sender=senderid&route=1&country=0
        #route=4, transactional sms & route=1, promotional sms
        payload = {'authkey': ssd_auth_key, 'mobiles': msisdn, 'message':message,'sender':ssd_sender_id,'route':'4'}
        r = requests.get(smsgw_ssd_url,params=payload)
        logging.debug(r.text)

class StatusUpdate(object):
    queue=STATUS_UPDATE_QUEUE

    @staticmethod
    def perform(data):
        to_users = data.get("to_users")
        data = data.get("data","")
        if data:
            for user in to_users:
                if user.msisdn:
                    GcmPush.perform({"msisdn": user.msisdn, "message": data})
                    logging.info("Status Update gcm push for msisdn: %s" % user.msisdn)

if __name__ == '__main__':
    queues = {NOTIFICATION_QUEUE: 5, GCM_QUEUE: 5}
    if len(sys.argv) > 1:
        obj = sys.argv[1]
        queues = json.loads(obj)
    tcount = 1
    for queue in queues:
        count = queues[queue]
        id = 1
        while id <= count:
           handler = QueueHandler(tcount, queue, id)
           handler.start()
           handlers.append(handler)
           tcount = tcount + 1
           id = id + 1

    logging.error('started all listeners')

    gevent.joinall(handlers)

    logging.error('No active handler')
