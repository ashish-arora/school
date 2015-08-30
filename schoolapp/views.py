from django.shortcuts import render
from .models import User
from rest_framework import status
from rest_framework.exceptions import ValidationError, AuthenticationFailed, ParseError
from rest_framework.exceptions import APIException
from schoolapp.helpers.json_response import JSONResponse
from rest_framework.views import APIView
import time, traceback, json
from helpers import utils
from mongoengine.errors import NotUniqueError
from mongoengine.errors import DoesNotExist
import base64, os
from models import User, Organization, Group
# Create your views here.
logger = utils.Logger.get_logger(__file__)
from models import VALID_TYPES, VALID_COUNTRY
from models import ADMIN, TEACHER, STUDENT, PARENT
from mongoengine.errors import DoesNotExist
from models import Attendance
from datetime import datetime, timedelta


class AccountSignUp:

    def post(self, request):
        try:
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

class AccountLogin:

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

    def get(self, request):
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