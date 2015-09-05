from django.shortcuts import render
from .models import User
from rest_framework import status
from rest_framework.exceptions import ValidationError, AuthenticationFailed, ParseError
from rest_framework.exceptions import APIException
from schoolapp.utils.json_response import JSONResponse
from rest_framework.views import APIView
import time, traceback, json
from utils import log
from mongoengine.errors import NotUniqueError
from mongoengine.errors import DoesNotExist
import base64, os
from models import User, Organization, Group
# Create your views here.
from models import VALID_TYPES, VALID_COUNTRY, VALID_ATTENDANCE_TYPES
from models import ADMIN, TEACHER, STUDENT, PARENT
from mongoengine.errors import DoesNotExist
from models import Attendance
from datetime import datetime, timedelta
from schoolapp.utils.helpers import authenticate_user
from utils.helpers import QueueRequests
from school.settings import NOTIFICATION_QUEUE
from rest_framework.views import APIView
from schoolapp.serializers import GroupSerializer, UserSerializer, OrganizationSerializer
from schoolapp.serializers import AttendanceSerializer
import bson, base64
BASE64_URLSAFE="-_"

logger = log.Logger.get_logger(__file__)


class AccountSignUp(APIView):

    def post(self, request):
        """
        Account Sign Up

        ---
        # YAML (must be separated by `---`)

        type:
            name:
                required: true
                type: string
            msisdn:
                required: true
                type: string
            type:
                required: true
                type: integer
            organization_id:
                required: true
                type: string
            group_id:
                required: true
                type: string

        serializer: UserSerializer
        omit_serializer: false

        parameters_strategy: merge
        omit_parameters:
            - path

        responseMessages:
            - code: 200
              message: Successfully Signed up
            - code: 400
              message: Bad Request
        """
        try:
            #import ipdb; ipdb.set_trace()
            name = request.data.get('name')
            msisdn = request.data.get('msisdn')
            type = request.data.get('type')
            organization_id = request.data.get('organization_id')
            group_id = request.data.get('group_id')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            raise ValidationError("Required parameter were not there")

        if type not in VALID_TYPES:
            raise ValidationError("Not valid user type")

        if msisdn.startswith("+"):
            if len(msisdn[1:]) != 12 or not msisdn[1:].isdigit():
                raise ValidationError("Invalid msisdn:%s" % msisdn)
            elif msisdn[:3] not in VALID_COUNTRY:
                raise ValidationError("Invalid country in msisdn: %s" % msisdn)
        elif not msisdn.isdigit() or not len(msisdn) == 10:
            raise ValidationError("Invalid country in msisdn: %s" % msisdn)

        try:
            group_id_list = json.loads(group_id)
        except Exception, ex:
            raise ValidationError("Invalid group id, cannot parse json")

        groups = Group.objects.filter(_id__in = group_id_list)

        if not len(groups) == len(group_id_list):
            raise ValidationError("Group Id data is not valid: %s" %(group_id))

        try:
            organization_obj = Organization.objects.get(_id= organization_id)
        except DoesNotExist:
            raise ValidationError("Invalid organization id :%s" % organization_id)

        token = base64.urlsafe_b64encode(os.urandom(8))

        try:
            User.objects.create(name=name, msisdn=msisdn, type=int(type), organization=organization_obj, groups=groups, token=token)
        except Exception, ex:
            logger.error("Error in signup: %s" % str(ex))
            return JSONResponse({"errorMsg": "Error occurred while user signup", "stat":"fail"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.debug("Successfully signed up for msisdn: %s" %(msisdn))
            return JSONResponse({"stat":"ok", "token":token})

class AccountLogin(APIView):

    def show_attendance(self, user):
        #get the student from the parent, make sure the student has been registered already
        childrens = User.objects.filter(parent_id=user.id)
        #gettting the information of present month
        month = datetime.today().month
        year = datetime.today().year
        from_date = datetime(year, month, 1)
        to_date = from_date + timedelta(days=31)
        result_dict = {}
        for child in childrens:
            result_dict[child.name]={}

        #prepare dic {'name1':{day1:0/1, day2:0/1}, 'name2':{day1:0/1, day2:0/1}}
        attendance_objs = Attendance.objects.filter(student__in=childrens, ts_gte=int(from_date.strftime("%s")), ts_lte = int(to_date.strftime("%s")))
        for attendance in attendance_objs:
            result_dict[attendance.student.name].update({datetime.fromtimestamp(attendance.ts): attendance.present})
        return result_dict


    def show_groups(self, user):
        #preparing data {'class1':[{'name1':'roll1'}, {'name2':'roll2'}], 'class2':[{'name1':'roll1'},..],..}
        group_ids = []
        result_dict = {}
        for group in user.groups:
            group_ids.append(group.id)
        group_objs = Group.objects.filter(id__in = group_ids)
        for group in group_objs:
            result_dict[group.name]={}
            for student_info_obj in group.members:
                result_dict[group.name].update({student_info_obj.student.name : student_info_obj.roll_no})
        return result_dict

    def post(self, request):
        """
        Account Login

        ---
        # YAML (must be separated by `---`)

        type:
            token:
                required: true
                type: string
            msisdn:
                required: true
                type: string
            type:
                required: true
                type: integer
            devices:
                required: true
                type: string
            country:
                required: true
                type: string


        serializer: UserSerializer
        omit_serializer: false

        parameters_strategy: merge
        omit_parameters:
            - path

        responseMessages:
            - code: 200
              message: Successfully Logged in
            - code: 400
              message: Bad Request
        """
        try:
            msisdn = request.data.get('msisdn')
            token = request.data.get('token')
            type = request.data.get('type')
            devices = request.data.get('devices')
            country = request.data.get('country')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            raise ValidationError("Required parameter were not there")
        try:
            devices = json.loads(devices)
        except Exception, ex:
            raise ParseError("Invalid json data: %s" % devices)

        try:
            user = User.objects.get(msisdn=msisdn, type=int(type), token=token)
        except Exception, ex:
            raise AuthenticationFailed("Invalid credentials,msisdn:%s, token:%s, type:%s" %(msisdn, token, type))

        try:
            user.devices = devices
            user.save()
        except Exception, ex:
            logger.error("Error while updating device info: %s, msisdn:%s" % (devices, msisdn))
            raise APIException("Error while saving data")

        #get attendance data depending on the user type\
        try:
            if type == PARENT:
                #show attendance
                result_dict = self.show_attendance(user)
                return JSONResponse({"parent_result":result_dict, "stat":"ok"}, status=status.HTTP_200_OK)
            else:
                result_dict = self.show_groups(user)
                return JSONResponse({"teacher_result":result_dict, "stat":"ok"}, status=status.HTTP_200_OK)
        except Exception, ex:
            logger.error("Error while getting info: %s" % str(ex))
            return JSONResponse({"stat":"fail", "errorMsg":"Error while getting information"})

class Attendance(APIView):

    #@authenticate_user
    def post(self, request):
        """
        Do Attendance

        ---
        # YAML (must be separated by `---`)

        type:
            attendance_data:
                required: true
                type: string
            group_id:
                required: true
                type: string

        serializer: AttendanceSerializer
        omit_serializer: false

        parameters_strategy: merge
        omit_parameters:
            - path

        responseMessages:
            - code: 200
              message: Successfully Signed up
            - code: 400
              message: Bad Request
        """
        try:
            attendance_data = request.data.get('attendance_data')
            group_id = request.data.get('group_id')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            raise ValidationError("Required parameter was not there")

        try:
            attendance_data = json.loads(attendance_data)
        except Exception, ex:
            raise ParseError("Invalid json data: %s" % attendance_data)

        try:
            group = Group.objects.get(id=group_id)
        except DoesNotExist:
            raise ValidationError("Group Id is invalid: %s" % group_id)
        attendance_objs = []
        for student_id, is_present in attendance_data.items():

            if is_present not in VALID_ATTENDANCE_TYPES:
                raise ValidationError("Invalid attendance type : %s " %(attendance_data))
            try:
                student = User.objects.get(id=student_id)
            except DoesNotExist, ex:
                raise DoesNotExist("Student id does not exist: %s" % student_id)

            attendance_objs.append(Attendance(student=student, present=int(is_present)))

            for parent_id in student.parent_ids:
                QueueRequests.enqueue(NOTIFICATION_QUEUE, {'id': parent_id, 'name': student.name})

        try:
            Attendance.objects.insert(attendance_objs)
        except Exception, ex:
            logger.error("Error occurred while saving the attendance doc: %s, data: %s, group_id:%s" % (str(ex), attendance_data, group_id))
            raise APIException("Error while saving data")
        return JSONResponse({"stat": "ok"})


class GroupView(APIView):

    #@authenticate_user
    def post(self, request):
        """
        Create Group

        ---
        # YAML (must be separated by `---`)

        type:
            name:
                required: true
                type: string
            organization_id:
                required: true
                type: string

        serializer: GroupSerializer
        omit_serializer: false

        parameters_strategy: merge
        omit_parameters:
            - path

        responseMessages:
            - code: 200
              message: Successfully Created the Group
            - code: 400
              message: Bad Request
        """
        try:
            name = request.data.get('name')
            organization_id = request.data.get('organization_id')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            raise ValidationError("Required parameter was not there")

        try:
            organization_id = str(bson.ObjectId(base64.b64decode(organization_id, BASE64_URLSAFE)))
            organization = Organization.objects.get(id=organization_id)
        except DoesNotExist:
            raise ValidationError("Organization Id is invalid: %s" % organization_id)

        try:
            group = Group.objects.create(name=name, organization=organization)
        except Exception, ex:
            logger.error("Error occurred while creating group: %s, name: %s, organization_id:%s" % (str(ex), name, organization_id))
            raise APIException("Error while saving data")
        else:
            group_id = base64.b64encode(group.id.binary, BASE64_URLSAFE)
            return JSONResponse({"stat": "ok", "group_id": group_id})

class OrganizationView(APIView):

    #@authenticate_user
    def post(self, request):
        """
        Create Organization

        ---
        # YAML (must be separated by `---`)

        type:
            name:
                required: true
                type: string
            city:
                required: true
                type: string
            state:
                required: true
                type: string
            country:
                required: true
                type: string
            address:
                required: true
                type: string

        serializer: OrganizationSerializer
        omit_serializer: false

        parameters_strategy: merge
        omit_parameters:
            - path

        responseMessages:
            - code: 200
              message: Successfully Created the Organization
            - code: 400
              message: Bad Request
        """
        try:
            name = request.data.get('name')
            country = request.data.get('country')
            city = request.data.get('city')
            state = request.data.get('state')
            address = request.data.get('address')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            raise ValidationError("Required parameter was not there")

        try:
            organization = Organization.objects.create(name=name, country=country, city=city, state=state, address=address)
        except Exception, ex:
            logger.error("Error occurred while creating organization doc: %s, name: %s, country:%s, city: %s, state:%s, address:%s " % (str(ex), name, country, city, state, address))
            raise APIException("Error while saving data")
        else:
            organization_id = base64.b64encode(organization.id.binary, BASE64_URLSAFE)
        return JSONResponse({"stat": "ok", "organization_id":organization_id})

