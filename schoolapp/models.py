from mongoengine import *
import time

ADMIN = 1
TEACHER = 2
STUDENT = 3
PARENT = 4

class User(Document):
    name = StringField(max_length=40)
    msisdn = ListField()
    devices = ListField(required=True)
    country = StringField(max_length=20)
    token = StringField(max_length=20)
    type= IntField(required=True)
    organization_id = StringField(max_length=20)
    parent_id = ObjectIdField(required=True)
    md = DictField(default={})
    group_id = ListField()
    ts = IntField(default=int(time.time()))

    meta = {
        'app_label':'mongo',
        'indexes':['msisdn']

    }

class Organization(Document):
    name = StringField(max_length=20)
    city = StringField(max_length=20)
    state = StringField(max_length=20)
    country = StringField()
    Address = StringField(max_length=50)

class Group(Document):
    name = StringField(max_length=20)
    organization_id = ReferenceField(Organization)
    members = ListField()

class Attendance(Document):
    pass

