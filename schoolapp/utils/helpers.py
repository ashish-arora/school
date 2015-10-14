__author__ = 'ashish'
from schoolapp.utils import log
import time, json
logging = log.Logger.get_logger(__file__)
from schoolapp.models import CustomUser, Student
from schoolapp.models import TEACHER, PARENT, ADMIN
from mongoengine.errors import *
import base64, bson
BASE64_URLSAFE="-_"
from school.settings import REDIS_CONN as cache
from schoolapp.models import Group, Status
import cStringIO
#from PIL import Image
import base64, uuid
from boto.s3 import bucket
from boto.s3.bucket import Key
from s3_connection import S3Connection
from school.settings import STATUS_UPLOAD_STORE
from school.settings import STATUS_UPDATE_QUEUE

def authenticate_user(func):
    """
    this will be called when the user has to be authenticated

    """
    def inner(self, request):
        username = self.request.data.get("username", None)
        password = self.request.data.get("password", None)
        try:
            user = CustomUser.objects.get(username=username)
        except DoesNotExist:
            raise ValidationError("User does not exist")
        else:
            if user.check_password(password):
                request.user = user
                return func(self, request)
            else:
                raise ValidationError("User's password is not correct")
    return inner

class QueueRequests():

    @staticmethod
    def enqueue(tag, data):
        data['ts'] = int(time.time())
        logging.debug('[QueueRequests] ' + tag)
        if tag is not None:
            cache.lpush('queue::' + tag, json.dumps(data))
        else:
            logging.error('invalid queue request')

def get_base64_decode(bson_id):
    return str(bson.ObjectId(base64.b64decode(str(bson_id), BASE64_URLSAFE)))

def get_base64_encode(object_id):
    return base64.b64encode(object_id.binary, BASE64_URLSAFE)

def create_teacher(name, msisdn, organization, token, username, groups=[], email='', password=''):
    try:
        user = CustomUser(first_name=name, last_name=name, msisdn=msisdn, type=TEACHER, organization=[organization], email=email, token=token, username=username)
        user.set_password(password)
        user.save()
        for group in groups:
            if user not in group.owner:
                group.owner.append(user)
                group.save()
        logging.debug("Created the teacher: %s" % user.id)
        return user.id
    #except NotUniqueError:
        #user=update_teacher(name, msisdn, organization, token, groups)
        #logging.debug("Update the teacher info: %s" %(user.id))
    #    return user.id
    except Exception, ex:
        logging.error("Error occurred while creating/updating teacher, name: %s, msisdn:%s, error:%s" %(name, msisdn, str(ex)))
        raise OperationError("Error occurred while creating/updating teacher, name: %s, msisdn:%s" %(name, msisdn))

def update_teacher(teacher, name, msisdn, organization, token='', type=TEACHER, groups=[], email='', password=''):
    try:
        if organization:
            teacher.organization=[organization]
        if token:
            teacher.token = token
        if name:
            teacher.first_name = name
        if email:
            teacher.email = email
        if password:
            teacher.set_password(password)
        if msisdn:
            teacher.msisdn = msisdn
        teacher.save()
        for group in groups:
            if teacher not in group.owner:
                group.owner.append(teacher)
                group.save()
        return teacher
    except Exception, ex:
        logging.error("Error occurred while updating teacher, name: %s, msisdn:%s, error:%s" %(name, msisdn, str(ex)))
        raise OperationError("Error occurred while updating teacher, name: %s, msisdn:%s" %(name, msisdn))

def create_parent(name, msisdn, organization, token, username, students=[], email='', password=''):
    try:
       parent = CustomUser.objects.create(first_name=name, last_name=name, msisdn=msisdn, type=PARENT, organization=[organization], token=token, username=username)
       if students:
           add_parent_to_student(parent, students)
       return parent.id
    except Exception, ex:
        logging.error("Error occurred while creating parent, name: %s, msisdn:%s, error:%s" %(name, msisdn, str(ex)))
        raise OperationError("Error occurred while creating parent, name: %s, msisdn:%s" %(name, msisdn))


def add_parent_to_student(parent, students=[]):
    try:
        for student in students:
            if parent not in student.parents:
                student.parents.append(parent)
                student.save()
    except Exception, ex:
        logging.error("Error occurred while adding parent in student table, parent: %s, students:%s, error:%s" %(parent.id, json.dumps(students), str(ex)))
        raise OperationError("Error occurred while adding parent in student table, parent: %s, students:%s" %(parent.id, json.dumps(students)))

def update_parent(parent, name, msisdn, organization, token='', type=PARENT, students=[], email='', password=''):
    try:
        if organization:
            parent.organization=[organization]
        if token:
            parent.token = token
        if name:
            parent.name = name
        if email:
            parent.email = email
        if password:
            parent.set_password(password)
        if msisdn:
            parent.msisdn = msisdn
        parent.save()
        for student in students:
            if parent not in student.parents:
                student.parents.append(parent)
                student.save()
        return parent
    except Exception, ex:
        logging.error("Error occurred while updating parent, name: %s, msisdn:%s, error:%s" %(name, msisdn, str(ex)))
        raise OperationError("Error occurred while updating parent, name: %s, msisdn:%s" %(name, msisdn))

def remove_parent_from_student(name, msisdn, organization, token, students=[]):
    try:
        user = CustomUser.objects.get(msisdn=msisdn, type=type)
        for student in students:
            if user in student.parents:
                student.parents.remove(user)
                student.save()
    except DoesNotExist:
        logging.error("User does not exist while removing parent: name: %s, msisdn: %s" %(name, msisdn))
        return
    except Exception, ex:
        logging.error("Error occurred while removing parent, name: %s, msisdn:%s, error:%s" %(name, msisdn, str(ex)))
        raise OperationError("Error occurred while removing parent, name: %s, msisdn:%s" %(name, msisdn))

def update_student(student,first_name,last_name,roll_no, group, parents=[]):
    try:
        add_student_to_group(student,group)
        remove_student_from_group(student,student.group)
        student.first_name = first_name
        student.last_name = last_name
        student.group = group
        student.roll_no = roll_no
        for parent in parents:
            if parent not in student.parents:
                student.parents.append(parent)
        student.save()

        return student.id
    except DoesNotExist:
        raise ValidationError("Student does not exist: first_name: %s ,last_name:%s, roll_no:%s" %(first_name,last_name, roll_no))
    except Exception, ex:
        logging.error("Error occurred while updating student, first_name: %s ,last_name: %s, roll_no:%s, error:%s" %(first_name,last_name, roll_no, str(ex)))
        raise OperationError("Error occurred while updating student, first_name: %s ,last_name: %s, roll_no:%s" %(first_name,last_name, roll_no))

def create_student(first_name,last_name, roll_no, group,organization, parents=[]):
    try:
        student = Student.objects.create(first_name=first_name,last_name=last_name, roll_no=roll_no, group=group,organization=organization)
        for parent in parents:
            if parent not in student.parents:
                student.parents.append(parent)
        student.save()
        add_student_to_group(student, group)
        return student.id
    except NotUniqueError:
        update_student(first_name,last_name, roll_no,group, parents)
    except Exception, ex:
        logging.error("Error occurred while creating student, first_name: %s ,last_name: %s, roll_no:%s, error:%s" %(first_name,last_name, roll_no, str(ex)))
        raise OperationError("Error occurred while creating student, first_name: %s ,last_name: %s, roll_no:%s" %(first_name,last_name, roll_no))

def add_student_to_group(student, group):
    try:
        if student not in group.members:
            group.members.append(student)
        group.save()
        return True
    except Exception, ex:
        logging.error("Error occurred while adding student to group, student: %s, group:%s, error:%s" %(student.id, group.id, str(ex)))
        raise OperationError("Error occurred while adding student to group,student: %s, group:%s" %(student.id, group.id))

def delete_student(student):
    grp = student.group
    try:
        remove_student_from_group(student,grp)
        student.delete()
    except Exception, ex:
        logging.error("Error occurred while deleting student profile: id: %s, %s" % (student.id, str(ex)))
        raise OperationError("Error occurred while deleting student profile group,student: %s, group:%s" %(student.id, grp.id))


def remove_student_from_group(student, group):
    try:
        group.members.remove(student)
        group.save()
        return True
    except ValueError:
        logging.error("Student is not in the group: student:%s , group:%s" %(student.id, group.id))
        return
    except Exception, ex:
        logging.error("Error occurred while removing student from group, student: %s, group:%s, error:%s" %(student.id, group.id, str(ex)))
        raise OperationError("Error occurred while removing student from group,student: %s, group:%s" %(student.id, group.id))

def create_admin(name, msisdn, organization, token):
    try:
        user = CustomUser.objects.create(name=name, msisdn=msisdn, type=ADMIN, organization=organization, token=token)
        logging.debug("Created the admin: %s" % user.id)
        return user.id
    except NotUniqueError:
        user = update_teacher(name, msisdn, organization, token, type=ADMIN)
        logging.debug("Updated the teacher info: %s" %(user.id))
        return user.id
    except Exception, ex:
        logging.error("Error occurred while creating/updating admin account, name: %s, msisdn:%s, error:%s" %(name, msisdn, str(ex)))
        raise OperationError("Error occurred while creating/updating admin account, name: %s, msisdn:%s" %(name, msisdn))


def get_groups(user, organization):
    if user.is_superuser:
        groups = Group.objects.filter(organization__in=organization)
    else:
        groups = Group.objects.filter(owner=user)
    return groups

def get_students(organization):
    return Student.objects.filter(organization__in=organization)

def get_teacher_owner_group(teacher):
    return Group.objects.filter(owner=teacher)

def get_group_list(user):
    organizations = user.organization
    groups = get_groups(user, organizations)
    owners = CustomUser.objects.filter(type=TEACHER, organization__in=organizations)
    members = Student.objects.filter(organization__in=organizations)
    return {"groups":groups, "organizations":organizations, "owners":owners, "members":members}

def get_teacher_view_data(user):
    teacher_groups=[]
    organizations = user.organization
    groups = get_groups(user, organizations)
    teachers = CustomUser.objects.filter(type=TEACHER, organization__in=organizations)
    for teacher in teachers:
        teacher_groups.append(get_teacher_owner_group(teacher))
    teachers = zip(teachers, teacher_groups)
    return {"teachers":teachers, "groups":groups, "teacher_groups": teacher_groups, "organizations":organizations}

def delete_teacher(teacher):
    Group.objects(owner=teacher).update(pull__owner=teacher)
    teacher.delete()

def get_parent_view_data(user):
    organizations = user.organization
    groups = get_groups(user, organizations)
    parents = CustomUser.objects.filter(type=PARENT, organization__in=organizations)
    all_students = Student.objects.filter(organization__in=organizations)
    students=all_students.filter(parents__in=parents)
    students_list=[]
    for parent in parents:
        temp_list=[]
        for student in students:
            if parent in student.parents:
                temp_list.append(student)
        students_list.append(temp_list)
    parents = zip(parents, students_list)
    return {"parents":parents, "organizations":organizations, "students": all_students}

def delete_parent(parent):
    Student.objects(parents=parent).update(pull__parents=parent)
    parent.delete()

def get_attendance_data(user):
    groups = Group.objects.filter(owner=user)
    students = Student.objects.filter(group__in=groups)
    return {"students":students, "groups":groups}

def upload_status_to_s3(user, x_session_id, body):
    conn = S3Connection.get_instance()
    bucket = conn.get_bucket(STATUS_UPLOAD_STORE)
    k = Key(bucket)
    k.key = x_session_id + '.' + str(user.id)
    fp = cStringIO.StringIO(body)
    k.set_contents_from_file(fp)

def get_status_key_from(user, x_session_id):
    encoded_upload_store = base64.b64encode(STATUS_UPLOAD_STORE, "-_")
    filekey = base64.b64encode(x_session_id + '.' + str(user.id), "-_")
    filekey = encoded_upload_store + filekey
    return filekey

def get_thumbnail(data):
    """img = Image.open(cStringIO.StringIO(data))
    if(img.mode!= 'RGB'):
        img = img.convert('RGB')
    thumbnail = cStringIO.StringIO()
    img.thumbnail((400, 400), Image.ANTIALIAS)
    img.save(thumbnail, "JPEG", quality=50, progressive=True)
    return base64.b64encode(thumbnail.getvalue())"""
    return None

def get_status(status_id, only_image=False):
    result={}
    status=Status.objects.get(id=status_id)
    if only_image:
        s3_key = status.image_key
        bucket_name = base64.b64decode(str(s3_key)[0:36],"-_")
        encoded_s3_handle = str(s3_key)[36:]
        padded_encoded_s3_handle = encoded_s3_handle + '=' * (-len(encoded_s3_handle) % 4)
        s3_handle = base64.b64decode(padded_encoded_s3_handle, "-_")
        conn = S3Connection.get_instance()
        bucket = conn.get_bucket(bucket_name)
        k = Key(bucket)
        k.key = s3_handle
        temp_file = cStringIO.StringIO()
        k.get_contents_to_file(temp_file)
        result['image'] = temp_file.getvalue()
        temp_file.close()
    result["id"]=str(status.id)
    result["message"]=status.message
    result["ts"]=status.ts
    return result

def get_to_users(user):
    return []

def post_status(user, data='', message='', to_users=[]):
    thumbnail = get_thumbnail(data)
    filekey=''
    if data:
        x_session_id = str(uuid.uuid4())
        upload_status_to_s3(user, x_session_id, data)
        filekey = get_status_key_from(user, x_session_id)
        filekey = filekey.strip("=")
    status=Status.objects.create(user=user, message=message, thumbnail=thumbnail, image_key=filekey)
    if to_users:
        QueueRequests.enqueue(STATUS_UPDATE_QUEUE, {"to_users":to_users, 'data':{"status_id": status.id, "image_key":status.image_key, "ts":status.ts, "tn":status.thumbnail, "message":status.message}})
    return status





