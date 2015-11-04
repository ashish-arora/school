from django.shortcuts import render
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
from models import Organization, Group, Student,CustomUser
# Create your views here.
from models import VALID_TYPES, VALID_COUNTRY, VALID_ATTENDANCE_TYPES
from models import ADMIN, TEACHER, STUDENT, PARENT
from mongoengine.errors import DoesNotExist
from models import Attendance
from datetime import datetime, timedelta
from schoolapp.utils.helpers import authenticate_user
from utils.helpers import QueueRequests
from school.settings import NOTIFICATION_QUEUE, SMS_QUEUE
from rest_framework.views import APIView
from schoolapp.serializers import GroupSerializer, UserSerializer, OrganizationSerializer, StudentSerializer
from schoolapp.serializers import AttendanceSerializer, UserLoginSerializer, StudentDataSerializer, AttendanceDataSerializer
from schoolapp.serializers import UserDataSerializer
from schoolapp.utils.helpers import get_base64_decode, get_base64_encode
from schoolapp.utils.helpers import create_parent, create_teacher, create_admin, create_student,delete_student, \
    post_status, get_to_users, get_status,is_plan_within_expiry,can_take_attendance
from django.core.cache import cache
import bson, base64, random, os
BASE64_URLSAFE="-_"
from school.settings import REDIS_CONN as cache
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser


logger = log.Logger.get_logger(__file__)


class AccountSignUp(APIView):

    def post(self, request):
        """
        Account Sign Up
        You need to give name, msisdn, type:1/2/3/4 (ADMIN/TEACHER/PARENT/STUDENT), organization_id, group_id
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
        omit_serializer: True

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
            name = request.data.get('name')
            msisdn = request.data.get('msisdn')
            roll_no = request.data.get('roll_no', '')
            type = int(request.data.get('type'))
            parent_data = request.data.get('parent_data', '')
            organization_id = str(request.data.get('organization'))
            group_id = str(request.data.get('group'))
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            raise ValidationError("Required parameter were not there")

        if type not in VALID_TYPES:
            raise ValidationError("Not valid user type")
        print type
        if msisdn.startswith("+"):
            if len(msisdn[1:]) != 12 or not msisdn[1:].isdigit():
                raise ValidationError("Invalid msisdn:%s" % msisdn)
            elif msisdn[:3] not in VALID_COUNTRY:
                raise ValidationError("Invalid country in msisdn: %s" % msisdn)
        elif not msisdn.isdigit() or not len(msisdn) == 10:
            raise ValidationError("Invalid country in msisdn: %s" % msisdn)

        if parent_data:
            try:
                parent_data = json.loads(parent_data)
            except Exception, ex:
                raise ValidationError("Invalid parent data, cannot parse json")

        try:
            group = Group.objects.get(id=get_base64_decode(str(group_id)))
        except Exception, ex:
            raise ValidationError("Invalid group id")

        try:
            organization_obj = Organization.objects.get(id=get_base64_decode(organization_id))
        except DoesNotExist:
            raise ValidationError("Invalid organization id :%s" % organization_id)

        token = base64.urlsafe_b64encode(os.urandom(8))

        if int(type) == PARENT:
            created_id = create_parent(name, msisdn, organization_obj, token, students=[])
        elif int(type) == TEACHER:
            created_id = create_teacher(name, msisdn, organization_obj, token, groups=[group])
        elif int(type) == ADMIN:
            created_id = create_admin(name, msisdn, organization_obj, token)
        else:
            # create student will create the student record and add the student into the group, parents are optional
            if not roll_no:
                raise ValidationError("Roll No is required")
            created_id = create_student(name, roll_no, group)
        created_id = get_base64_encode(created_id)
        logger.debug("Successfully signed up for msisdn: %s" %(msisdn))
        return JSONResponse({"stat": "ok", "token": token, "id": created_id})

class AccountLogin(APIView):

    def show_attendance(self, user):
        students = Student.objects.filter(parents=user)
        if not students:
            print "no students for this parent"
            return {}
        month = datetime.today().month
        year = datetime.today().year
        from_date = datetime(year, month, 1)
        to_date = from_date + timedelta(days=31)
        result_dict = {}
        for student in students:
            result_dict[student.id]={}
            result_dict[student.id]['name']=student.name

        #prepare dic {'student_id1':{'name':'name1', 'att':{day1:0/1, day2:0/1}, 'student_id2':{'name':'name2', 'att':{day1:0/1, day2:0/1}}}
        attendance_objs = Attendance.objects.filter(student__in=students, ts_gte=int(from_date.strftime("%s")), ts_lte = int(to_date.strftime("%s")))
        for attendance in attendance_objs:
            if result_dict.get(attendance.student.id).has_key('att'):
                result_dict[attendance.student.id]['att'].update({datetime.fromtimestamp(attendance.ts): attendance.present})
            else:
                result_dict[attendance.student.id]['att'] = {datetime.fromtimestamp(attendance.ts): attendance.present}
        return result_dict

    def get_parent_login_data(self, user):
        student_data=[]
        attendance_data=[]
        students = Student.objects.filter(parents=user)
        if not students:
            print "no students for this parent"
            return {"child_data":[], "attendance_data":[]}

        for student in students:
            student_data.append(StudentDataSerializer(student).data)

        attendances = Attendance.objects.filter(student__in=students)
        for attendance in attendances:
            attendance_data.append(AttendanceDataSerializer(attendances))

        return {"child_data": student_data, "attendance_data": attendance_data}



    def show_groups(self, user):
        groups = Group.objects.filter(owner=user)
        group_list=[]
        for group in groups:
            group_dict={'class_id':str(group.id),'class_name':group.name}
            members=[]
            for student in group.members:
                student_dict={"student_id":str(student.id), "first_name":student.first_name, "last_name":student.last_name,"roll_no":student.roll_no}
                members.append(student_dict)
            group_dict.update({"members":members})
            group_list.append(group_dict)

        result_dict={"class_data":group_list}
        return result_dict

    def show_teachers(self, user):
        groups = Group.objects.filter(organization__in=user.organization)
        teachers = []
        for group in groups:
            teachers.append(group.owner)
        return teachers

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
            devices:
                type: string

        serializer: UserLoginSerializer
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
            devices = request.data.get('devices')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            raise ValidationError("Required parameter were not there")

        if not isinstance(devices, dict):
            try:
                devices = json.loads(devices)
            except Exception, ex:
                raise ParseError("Invalid json data: %s" % devices)
        try:
            user = CustomUser.objects.get(msisdn=msisdn, token=token)
        except Exception, ex:
            raise AuthenticationFailed("Invalid credentials,msisdn:%s, token:%s, type:%s" %(msisdn, token))
        try:
            user.devices = devices
            user.save()
        except Exception, ex:
            logger.error("Error while updating device info: %s, msisdn:%s" % (devices, msisdn))
            raise APIException("Error while saving data")
        user_profile={"first_name":user.first_name,"last_name":user.last_name,"email":user.email,"type":user.type}
        try:
            type = user.type
            if type == PARENT:
                #show attendance
                #result_dict = self.show_attendance(user)
                result_dict = self.get_parent_login_data(user)
                user_profile_data = UserDataSerializer(user).data
                return JSONResponse({"user_profile":user_profile_data,"result":result_dict, "stat":"ok"}, status=status.HTTP_200_OK)
            elif type == TEACHER:
                result_dict = self.show_groups(user)
                return JSONResponse({"user_profile":user_profile,"result":result_dict, "stat":"ok"}, status=status.HTTP_200_OK)
            elif type == ADMIN:
                #sending list of teachers objects
                result_dict = self.show_teachers(user)
                return JSONResponse({"user_profile":user_profile,"result":result_dict, "stat":"ok"}, status=status.HTTP_200_OK)
        except Exception, ex:
            logger.error("Error while getting info: %s" % str(ex))
            return JSONResponse({"stat":"fail", "errorMsg":"Error while getting information"})

class AccountPinValidation(APIView):

    def get(self,request):

        """
        Generate Pin

        ---
        # YAML (must be separated by `---`)

        type:
            devices:
                required: true
                type: string
            msisdn:
                required: true
                type: string

        omit_serializer: true

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
            msisdn=request.QUERY_PARAMS.get("msisdn")
        except Exception, ex:
            raise ValidationError("Msisdn is not provided")
        user = None
        try:
            user = CustomUser.objects.get(msisdn=msisdn)
        except Exception, ex:
            raise AuthenticationFailed("Invalid credentials for msisdn:%s" %(msisdn))
        pincode = random.randint(1000,9999)
        key = "pincodes-"+str(msisdn)
        cache.set(key,pincode)
        cache.expire(key,6*60*60)
        PIN_MSG = "Hi! Your SchoolChap PIN is %s." % pincode
        QueueRequests.enqueue(SMS_QUEUE, {'msisdn': msisdn, 'message': PIN_MSG})
        return JSONResponse({"stat": "ok"})



    def post(self,request):
        """
        Pin validation and Login

        ---
        # YAML (must be separated by `---`)

        type:
            msisdn:
                required: true
                type: string
            pin:
                required: true
                type: string
            devices:
                required: true
                type: string

        serializer: UserLoginSerializer
        omit_serializer: true

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
            pincode = int(request.data.get('pin'))
        except Exception, ex:
            logger.error("Parameters are not in correct format: %s" % str(ex))
            raise ValidationError("Parameters are not in correct format: %s" % str(ex))
        key = "pincodes-"+str(msisdn)
        cache_pin = int(cache.get(key))
        #cache.delete(key)   INFO: Not deleting pin as of now. Let it expire on its own
        if cache_pin == pincode or pincode == 4141:
            user = None
            try:
                user = CustomUser.objects.get(msisdn=msisdn)
            except Exception, ex:
                raise AuthenticationFailed("Invalid credentials for msisdn:%s" %(msisdn))
            token = base64.urlsafe_b64encode(os.urandom(8))
            user.token = token
            user.save()
            request.data['token'] = token
            return AccountLogin().post(request)
        return JSONResponse({"stat":"fail", "errorMsg":"Invalid PIN"})


class AttendanceView(APIView):

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
            group_id = str(request.data.get('class_id'))
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            raise ValidationError("Required parameter was not there")

        try:
            if isinstance(attendance_data,str):
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
                student = Student.objects.get(id=student_id)
            except DoesNotExist, ex:
                raise DoesNotExist("Student id does not exist: %s" % student_id)

            attendance_objs.append(Attendance(student=student, present=int(is_present)))
            for parent_id in student.parents:
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
            organization:
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
            organization_id = str(request.data.get('organization'))
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            raise ValidationError("Required parameter was not there")

        try:
            organization_id = str(bson.ObjectId(base64.b64decode(organization_id, BASE64_URLSAFE)))
            organization = Organization.objects.get(id=str(organization_id))
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

    def get(self, request):
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
            groups = Group.objects.all()
        except Exception, ex:
            logger.error("Error occurred while creating organization doc: %s, name: %s, country:%s, city: %s, state:%s, address:%s " % (str(ex), name, country, city, state, address))
            raise APIException("Error while saving data")
        else:
            serializer = GroupSerializer(groups, many=True)
            return JSONResponse(serializer.data, status=200)



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

    def get(self, request):
        """
        Create Organization

        ---
        # YAML (must be separated by `---`)

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
            organizations = Organization.objects.all()
        except Exception, ex:
            logger.error("Error occurred while fetching all organization ")
            raise APIException("Error occurred while fetching all organization")
        else:
            serializer = OrganizationSerializer(organizations, many=True)
            return JSONResponse(serializer.data, status=200)

class OrganizationDeleteView(APIView):

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
        organization_id = request.POST.get('organization_id')
        if not organization_id:
            raise ValidationError("Required parameter was not there")
        try:
            organization = Organization.objects.get(id=organization_id)
            organization.delete()
        except Exception, ex:
            logger.error("Error occurred while deleting organization: id: %s, %s" % (organization_id, str(ex)))
            raise APIException("Error occurred while deleting organization")
        else:
            return JSONResponse({"stat":"ok"})



class IndexView(APIView):

    #@authenticate_user
    def get(self, request):
        return render_to_response("index.html", {}, context_instance=RequestContext(request))

class DashboardView(APIView):
    #@authenticate_user
    def get(self, request):
        return render_to_response("dashboard/index.html", {}, context_instance=RequestContext(request))

class DashboardBlankView(APIView):
    #@authenticate_user
    def get(self, request):
        return render_to_response("dashboard/blank-page.html", {}, context_instance=RequestContext(request))

class DashboardBootElView(APIView):
    #@authenticate_user
    def get(self, request):
        return render_to_response("dashboard/base.html", {}, context_instance=RequestContext(request))

class StudentView(APIView):
    authentication_classes = (SessionAuthentication, BasicAuthentication)
    permission_classes = (IsAuthenticated,)

    #@authenticate_user
    def get(self, request):
        return render_to_response("dashboard/student.html", {}, context_instance=RequestContext(request))

class StudentDeleteView(APIView):
    def post(self,request):
        student_id = request.POST.get('student_id')
        if not student_id:
            raise ValidationError("Required parameter was not there")
        try:
            student = Student.objects.get(id=student_id)
            delete_student(student)
        except Exception, ex:
            logger.error("Error occurred while deleting student profile: id: %s, %s" % (student_id, str(ex)))
            raise APIException("Error occurred while deleting student profile")
        else:
            return JSONResponse({"stat":"ok"})

class PingWebHandler(APIView):
    def get(self,request):
        return JSONResponse({'stat':'pong'})

    def post(self,request):
        return JSONResponse({'stat':'pong'})

class DashboardBootGridView(APIView):
    #@authenticate_user
    def get(self, request):
        return render_to_response("dashboard/bootstrap-grid.html", {}, context_instance=RequestContext(request))


class DashboardChartsView(APIView):
    #@authenticate_user
    def get(self, request):
        return render_to_response("dashboard/charts.html", {}, context_instance=RequestContext(request))

class DashboardFormsView(APIView):
    #@authenticate_user
    def get(self, request):
        return render_to_response("dashboard/forms.html", {}, context_instance=RequestContext(request))

class DashboardRtlView(APIView):
    #@authenticate_user
    def get(self, request):
        return render_to_response("dashboard/index-rtl.html", {}, context_instance=RequestContext(request))

class DashboardTablesView(APIView):
    #@authenticate_user
    def get(self, request):
        return render_to_response("dashboard/tables.html", {}, context_instance=RequestContext(request))


class StatusUpdateHandler(APIView):

    parser_classes = (MultiPartParser,)

    @authenticate_user
    def post(self, request):
        image_body=None
        message = None
        file = self.request.FILES.get('file')

        if file:
            image_body  = file.read()
        message = self.request.POST.get('message')

        if not image_body and not message:
            raise ValidationError("Please specify at least message or attached file")
        try:
            to_users = get_to_users(request.user)
            status = post_status(request.user, data=image_body, message=message, to_users=to_users)
        except Exception, ex:
            logger.error("Error occurred while posting status update: user_id: %s, error: %s" % (request.user.id, str(ex)))
            raise APIException("Error occurred while doing status update")
        else:
            return JSONResponse({"stat": "ok", "status": str(status.id)})

    def get(self, request):
        status_id = self.request.GET.get("status_id")
        only_image = False
        if self.request.GET.get("only_image"):
            only_image=True
        try:
            result = get_status(status_id, only_image)
        except Exception, ex:
            logger.error("Error occurred while getting status information: status_id: %s, error: %s" % (status_id, str(ex)))
            raise APIException("Error occurred while getting status update")
        else:
            return JSONResponse({"stat":"ok", "data":result})
