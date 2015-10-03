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
from schoolapp.models import Group

def authenticate_user(func):
    """
    this will be called when the user has to be authenticated

    """
    def inner(self, request):
        username = self.request.data.get("username", None)
        password = self.request.data.get("password", None)
        try:
            user = User.objects.get(username=username, password=password)
        except DoesNotExist:
            raise ValidationError("User does not exist")
        else:
            request.user = user
            return func(self, request)
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
        user = CustomUser(first_name=name, last_name=name, msisdn=msisdn, type=TEACHER, organization=[organization], token=token, username=username)
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

def update_teacher(teacher, name, msisdn, organization, token, type=TEACHER, groups=[], email='', password=''):
    try:
        #user = CustomUser.objects.get(msisdn=msisdn, type=type)
        #user.groups = list(set(user.groups.append(groups)))
        if organization:
            teacher.organization=organization
        if token:
            teacher.token = token
        if name:
            teacher.name = name
        if email:
            teacher.email = email
        if password:
            teacher.password = password
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

def create_parent(name, msisdn, organization, token, students=[]):
    try:
       user = User.objects.create(name=name, msisdn=msisdn, type=PARENT, organization=organization, token=token)
       if students:
           add_parent_to_student(user, students)
       return user.id
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

def update_parent(name, msisdn, organization, token, students=[]):
    try:
        user = User.objects.get(msisdn=msisdn, type=type)
        #user.groups = list(set(user.groups.append(groups)))
        user.organization=organization
        user.token = token
        user.save()
        for student in students:
            if user not in student.parents:
                student.parents.append(user)
                student.save()
        return user
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

def update_student(name, roll_no, parents=[]):
    try:
        student = Student.objects.get(name=name, roll_no=roll_no)
        for parent in parents:
            if parent not in student.parents:
                student.parents.append(parent)
        student.save()
        return student.id
    except DoesNotExist:
        raise ValidationError("Student does not exist: name:%s, roll_no:%s" %(name, roll_no))
    except Exception, ex:
        logging.error("Error occurred while updating student, name: %s, roll_no:%s, error:%s" %(name, roll_no, str(ex)))
        raise OperationError("Error occurred while updating student, name: %s, roll_no:%s" %(name, roll_no))

def create_student(name, roll_no, group, parents=[]):
    try:
        student = Student.objects.create(name=name, roll_no=roll_no, group=group)
        for parent in parents:
            if parent not in student.parents:
                student.parents.append(parent)
        student.save()
        add_student_to_group(student, group)
        return student.id
    except NotUniqueError:
        update_student(name, roll_no, parents)
    except Exception, ex:
        logging.error("Error occurred while creating student, name: %s, roll_no:%s, error:%s" %(name, roll_no, str(ex)))
        raise OperationError("Error occurred while creating student, name: %s, roll_no:%s" %(name, roll_no))

def add_student_to_group(student, group):
    try:
        if student not in group.members:
            group.members.append(student)
        group.save()
        return True
    except Exception, ex:
        logging.error("Error occurred while adding student to group, student: %s, group:%s, error:%s" %(student.id, group.id, str(ex)))
        raise OperationError("Error occurred while adding student to group,student: %s, group:%s" %(student.id, group.id))

def remove_student_from_group(student, group):
    try:
        group.members.remove(student)
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


