from mongoengine import *
import time

ADMIN = 1
TEACHER = 2
STUDENT = 3
PARENT = 4

PRESENT = 1
ABSENT = 0

VALID_TYPES = [ADMIN, TEACHER, STUDENT, PARENT]

VALID_COUNTRY = ['+91']

VALID_ATTENDANCE_TYPES = [PRESENT, ABSENT]

class User(Document):
    name = StringField(max_length=40)
    msisdn = ListField()
    devices = ListField(required=True)
    country = StringField(max_length=20)
    token = StringField(max_length=20)
    type= IntField(required=True)
    organization = StringField(max_length=20)
    parent_id = ListField(required=True)
    md = DictField(default={})
    groups = ListField(ReferenceField('Group'))
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
    address = StringField(max_length=50)

class StudentInfo(Document):
    student = ReferenceField(User)
    parent = ListField(ReferenceField(User))
    roll_no = IntField(required=True)

class Group(Document):
    name = StringField(max_length=20)
    organization_id = ReferenceField(Organization)
    members = ListField(ReferenceField(StudentInfo))

class Attendance(Document):
    student=ReferenceField(User)
    ts= IntField(default=int(time.time()))
    present = IntField()
