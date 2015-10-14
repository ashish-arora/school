from mongoengine import *
from mongoengine.django.auth import User
import time

ADMIN = 1
TEACHER = 2
STUDENT = 4
PARENT = 3

PRESENT = 1
ABSENT = 0

VALID_TYPES = [ADMIN, TEACHER, STUDENT, PARENT]

USER_TYPE = (ADMIN, TEACHER, PARENT)

VALID_COUNTRY = ['+91']

VALID_ATTENDANCE_TYPES = [PRESENT, ABSENT]

PRODUCT_TYPES = (0, 1)

PRODUCT_TYPE_NAMES = ('BASIC', 'PREMIUM')

class CustomUser(User):
    msisdn = StringField(max_length=15, unique_with='type', required=True)
    devices = DictField(required=False)
    country = StringField(max_length=20)
    token = StringField(max_length=20)
    type= IntField(required=True, choices=USER_TYPE)
    organization = ListField(ReferenceField('Organization'))
    md = DictField(default={})
    ts = IntField(default=int(time.time()))

    meta = {
        'allow_inheritance': True,
        'indexes': [
            {'fields': ['username'], 'unique': True, 'sparse': True}, 'msisdn', 'type'
        ]
    }

"""class User(Document):
    name = StringField(max_length=40, required=True)
    msisdn = StringField(max_length=15, unique_with='type', required=True)
    devices = DictField(required=False)
    country = StringField(max_length=20)
    token = StringField(max_length=20)
    type= IntField(required=True, choices=USER_TYPE)
    organization = ReferenceField('Organization')
    md = DictField(default={})
    ts = IntField(default=int(time.time()))

    meta = {
        'app_label':'mongo',
        'indexes':['msisdn', 'type']

    }
"""

class Organization(Document):
    name = StringField(max_length=20)
    city = StringField(max_length=20)
    state = StringField(max_length=20)
    country = StringField()
    address = StringField(max_length=50)
    product_type=ReferenceField('ProductType')


class Student(Document):
    first_name=StringField(max_length=20)
    last_name=StringField(max_length=20)
    roll_no = IntField(unique_with='group')
    parents = ListField(ReferenceField(CustomUser))
    group = ReferenceField('Group')
    organization=ReferenceField('Organization')

    meta={
        'indexes':['roll_no', 'parents']
    }

class Group(Document):
    name = StringField(max_length=20)
    organization = ReferenceField(Organization)
    members = ListField(ReferenceField(Student))
    owner = ListField(ReferenceField(CustomUser))

    meta={
        'indexes': ['owner']
    }

class Attendance(Document):
    student=ReferenceField(Student)
    ts= IntField(default=int(time.time()))
    present = IntField(required=True)

    meta={
        'indexes': ['ts', 'student']
    }

class AttendanceSummary(Document):
    group=ReferenceField('Group')
    ts=IntField(default=int(time.time()))
    present=IntField(required=True)
    absent=IntField(required=True)

class Status(Document):
    user = ReferenceField(CustomUser)
    message = StringField()
    ts=IntField(default=int(time.time()))
    thumbnail=StringField()
    image_key=StringField()


class ProductType(Document):
    name= StringField(required=True, choices=PRODUCT_TYPE_NAMES)
    type= IntField(required=True, choices=PRODUCT_TYPES)
    free_students=IntField(required=True)
    features=ListField()

class Transactions(Document):
    organization = ReferenceField(Organization)
    payment = IntField(required=True)
    ts=IntField(default=time.time())

