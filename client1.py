import xmpp
import base64, bson

import uuid

token = uuid.uuid4()[:15]
id = str(uuid.uuid4()[:15]) + "@127.0.0.1"

jid = xmpp.JID(jid)
client = xmpp.client(jid.domain)
client.connect()
client.auth(jid.node, token, '')
client.send(xmpp.Message(jabber_id, "My first message"))



