__author__ = 'ashish'

from school.settings import ADMIN_JID, ADMIN_JABBER_PASSWORD, JABBER_PORT
from school.settings import JABBER_SERVER
from schoolapp.utils import log
import xmpp, traceback, json

logger = log.Logger.get_logger(__file__)

class JabberClient:

    jabber_instance=None

    def __init__(self, jid=ADMIN_JID, password=ADMIN_JABBER_PASSWORD, port=JABBER_PORT, server=JABBER_SERVER):
        self.jid = jid
        self.password = password
        self.port = port
        self.jabber_obj = self.authenticate_jabber_user()
        self.server = server

    @classmethod
    def get_jabber_instance(cls):
        if not JabberClient.jabber_instance:
            cls.jabber_instance = JabberClient(ADMIN_JID, ADMIN_JABBER_PASSWORD)
            return cls.jabber_instance
        return cls.jabber_instance

    def authenticate_jabber_user(self):
        try:
            jabber = None
            logger.debug("Authenticating Jabber user")
            jid = xmpp.protocol.JID(self.jid)
            jabber = xmpp.Client(jid.getDomain(),debug= [])
            jabber.connect(server=(jid.getDomain(), self.port))
            jabber.auth(jid.getNode(), self.password)
        except:
            logger.error("Error Occurred : %s" % traceback.format_exc())
        return jabber

    def send_message(self, jabber_id, message_dic):
        try:
            if not self.jabber_obj.connected:
                logger.debug("Jabber User is not connected trying to reconnect")
                self.jabber_obj= self.authenticate_jabber_user()
            message_dic = json.dumps(message_dic)
            jabber_id = jabber_id + '@' + self.server
            self.jabber_obj.send(xmpp.Message(jabber_id, message_dic))
            logger.debug("message has been send to id:%s" % jabber_id)
        except:
            logger.error("Error Occurred : %s" % traceback.format_exc())
