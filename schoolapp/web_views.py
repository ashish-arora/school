__author__ = 'ashish'
from django.views.generic import View
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
#from schoolapp.models import User
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, logout
from mongoengine.django.auth import User
from schoolapp.models import CustomUser
from mongoengine.django.mongo_auth import models
from mongoengine.queryset import DoesNotExist
from schoolapp.models import Organization, Student, Group
import bson, base64, random, os
BASE64_URLSAFE="-_"
from utils import log
from forms import OrganizationForm
import json
from models import TEACHER
from utils.helpers import get_groups, create_teacher, update_teacher, get_teacher_owner_group,get_students,create_student,update_student

logger = log.Logger.get_logger(__file__)

class StudentView(View):
    template_name='student.html'

    def get(self, request):
        # <view logic>
        organizations = request.user.organization
        groups = get_groups(request.user, organizations)
        students = get_students(organizations)
        return render(request, self.template_name, {"groups":groups,"students":students})

    def post(self, request,id=None):
        errors=[]
        message=None
        post_type='post'
        grp = None
        organization = request.user.organization
        if self.args:
            id=self.args[0]
            post_type='update'
        try:
            first_name = request.POST.get('first_name_modal')
            last_name = request.POST.get('last_name_modal')
            roll_no = request.POST.get('roll_no_modal')
            groupid = request.POST.get('class_value_modal')
            grp = Group.objects.get(id=groupid)
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            errors.append("Required parameter was not there")
            request.POST.post_type = post_type
            return render(request, self.template_name, {'errors':errors})

        if (first_name or last_name) and roll_no and groupid:
            if id:
                # to handle update request
                try:
                    student = Student.objects.get(id=id)
                except Exception, ex:
                    logger.error("Organization does not exist :%s" % id)
                    errors.append("Error occurred while updating record, Please try again")
                    request.POST.post_type = post_type
                else:
                    update_student(student,first_name=first_name,last_name=last_name,roll_no=roll_no,group=grp)
                    message = "Student information has been successfully updated"
            else:
                try:
                    org = organization[0]
                    create_student(first_name=first_name, last_name=last_name, roll_no=roll_no, group=grp, organization=org)
                except Exception, ex:
                    #request.POST.set("post_type", post_type)
                    #request.POST.post_type = post_type
                    logger.error("Error occurred while creating Student doc: %s, first_name: %s, last_name:%s, roll_no: %s, class_value:%s" % (str(ex), first_name, last_name, roll_no,groupid ))
                    errors.append("Error while saving data, please try again")
                else:
                    message = "Student profile has been successfully created"
        else:
            errors.append("Required parameter was not there")
            request.POST.post_type = post_type
        groups = get_groups(request.user, organization)
        students = get_students(organization)
        return render(request, self.template_name, {"errors": errors, "message": message, 'organization':organization,'groups':groups,"students":students})

class GroupDeleteView(View):
    template_name = 'group.html'

    def post(self, request):
        errors=[]
        message=None
        try:
            if self.args:
                id=self.args[0]
                group = Group.objects.get(id=id)
                group.delete()
                message = "Group has been successfully deleted"
            else:
                errors.append("Please specify group id")
        except Exception, ex:
            logger.error("Error occurred while group deletion: %s" % id)
            errors.append("Error occurred while group deletion")
        groups = Group.objects.filter(owner=request.user)
        return render(request, self.template_name, {"groups": groups, "errors": errors, "message": message})

class GroupView(View):
    template_name='group.html'

    def get(self, request):
        # <view logic>
        organizations = request.user.organization
        groups = get_groups(request.user, organizations)
        owners = CustomUser.objects.filter(type=TEACHER, organization__in=organizations)
        members = Student.objects.filter(organization__in=organizations)
        return render(request, self.template_name, {"groups":groups, "organizations":organizations, "owners":owners, "members":members})

    def post(self, request, id=None):
        errors=[]
        message=None
        post_type='post'
        if self.args:
            id=self.args[0]
            post_type='update'
        try:
            name = request.POST.get('name')
            organization_id = request.POST.get('organization_id')
            members = request.POST.get('members')
            owner = request.POST.get('owner')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            errors.append("Required parameter was not there")
            request.POST.post_type = post_type
            return render(request, self.template_name, {'errors':errors})
        if not name or not organization_id:
            errors.append("Required parameter was not there")
            request.POST.post_type = post_type
            return render(request, self.template_name, {'errors':errors})
        if members:
            try:
                members = json.loads(members)
            except Exception, ex:
                errors.append("Members are not in correct format")
                return render(request, self.template_name, {"errors": errors, "message": message})
            else:
                if not isinstance(members, list):
                    errors.append("Members are not in correct format")
                    return render(request, self.template_name, {"errors": errors, "message": message})
                members = Student.objects.filter(id__in=members)
        if owner:
            try:
                owner = json.loads(owner)
            except Exception, ex:
                errors.append("Owner is not in correct format")
                return render(request, self.template_name, {"errors": errors, "message": message})
            else:
                if not isinstance(owner, list):
                    errors.append("Owner are not in correct format")
                    return render(request, self.template_name, {"errors": errors, "message": message})
                owner = User.objects.filter(id__in=owner)
        try:
            organization = Organization.objects.get(id=organization_id)
        except Exception, ex:
            errors.append("Organization does not exist")
            logger.error("Organization does not exist: %s" % organization_id)
            return render(request, self.template_name, {"errors": errors, "message": message})
        if id:
            # to handle update request
            try:
                group = Group.objects.get(id=id)

            except Exception, ex:
                logger.error("Group does not exist :%s" % id)
                errors.append("Error occurred while updating record, Please try again")
            else:
                group.name = name
                group.organization = organization
                if members:
                    group.members=members
                if owner:
                    group.owner = owner
                group.save()
                message = "Group has been successfully updated"
                groups = get_groups(request.user, [organization])
            return render(request, self.template_name, {"errors": errors, "message": message, 'group':group, "groups": groups})
        else:
            # to handle create request
            try:
                group = Group.objects.create(name=name, organization=organization, members=members, owner=owner)
            except Exception, ex:
                request.POST.post_type = post_type
                logger.error("Error occurred while creating group:%s" % str(ex))
                errors.append("Error while saving data, please try again")
            else:
                groups = get_groups(request.user, [organization])
                message = "Group has been successfully created"
            return render(request, self.template_name, {"groups": groups, "errors": errors, "message": message})

class TeacherDeleteView(View):
    template_name = 'teacher.html'

    def post(self, request):
        errors=[]
        message=None
        try:
            if self.args:
                id=self.args[0]
                teacher = CustomUser.objects.get(id=id)
                teacher.delete()
                message = "Teacher has been successfully deleted"
            else:
                errors.append("Please specify teacher id")
        except Exception, ex:
            logger.error("Error occurred while teacher deletion: %s" % id)
            errors.append("Error occurred while teacher deletion")
        teachers = CustomUser.objects.filter(type=TEACHER, organization__in=request.user.organizations)
        organizations = request.user.organization
        groups = get_groups(request.user, organizations)
        return render(request, self.template_name, {"teachers": teachers, "errors": errors, "message": message, "groups":groups})

class ParentsView(View):
    pass

class ParentsDeleteView(View):
    pass

class TeacherView(View):
    template_name='teacher.html'

    def get_teacher_view_data(self, request):
        organizations = request.user.organization
        groups = get_groups(request.user, organizations)
        teachers = CustomUser.objects.filter(type=TEACHER, organization__in=organizations)
        #members = Student.objects.filter(organization__in=organizations)
        for teacher in teachers:
            teacher.groups = get_teacher_owner_group(teacher)
        return {"teachers":teachers, "groups":groups, "organizations":organizations}

    def get(self, request):
        # <view logic>
        teacher_groups=[]
        organizations = request.user.organization
        groups = get_groups(request.user, organizations)
        teachers = CustomUser.objects.filter(type=TEACHER, organization__in=organizations)
        #members = Student.objects.filter(organization__in=organizations)
        for teacher in teachers:
            teacher_groups.append(get_teacher_owner_group(teacher))
        teachers = zip(teachers, teacher_groups)
        return render(request, self.template_name, {"teachers":teachers, "groups":groups, "teacher_groups": teacher_groups, "organizations":organizations})

    def post(self, request, id=None):
        errors=[]
        message=None
        post_type='post'
        if self.args:
            id=self.args[0]
            post_type='update'
        try:
            name = request.POST.get('name')
            msisdn = request.POST.get('msisdn')
            email = request.POST.get('email')
            username = request.POST.get('username')
            group_ids = request.POST.getlist("group_id[]")
            organization_id = request.POST.get('organization_id')
            password = request.POST.get('password')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            errors.append("Required parameter was not there")
            request.POST.post_type = post_type
            data = self.get_teacher_view_data(request)
            data.update({'errors':errors})
            return render(request, self.template_name, data)
        if not name or not group_ids or not msisdn or not username or not email or not organization_id:
            errors.append("Required parameter was not there")
            request.POST.post_type = post_type
            data = self.get_teacher_view_data(request)
            data.update({'errors':errors})
            return render(request, self.template_name, data)
        groups = Group.objects.filter(id__in=group_ids)
        try:
            organization = Organization.objects.get(id=organization_id)
        except Exception, ex:
            errors.append("Organization does not exist")
            logger.error("Organization does not exist: %s" % organization_id)
            data = self.get_teacher_view_data(request)
            data.update({'errors':errors, "message": message})
            return render(request, self.template_name, data)
        teachers=[]
        if id:
            # to handle update request
            try:
                teacher = CustomUser.objects.get(id=id)
                update_teacher(teacher, name, msisdn, organization, type=TEACHER, groups=groups, email=email, password=password)
            except Exception, ex:
                logger.error("Teacher does not exist :%s" % id)
                errors.append("Error occurred while updating record, Please try again")
            else:

                message = "Teacher has been successfully updated"
                organizations = request.user.organization
                teachers = CustomUser.objects.filter(type=TEACHER, organization__in=organizations)
                groups = get_groups(request.user, organizations)
                for teacher in teachers:
                    teacher.groups = get_teacher_owner_group(teacher)
            return render(request, self.template_name, {"errors": errors, "message": message, 'teachers':teachers, "groups":groups})
        else:
            # to handle create request
            try:
                token = base64.urlsafe_b64encode(os.urandom(8))
                create_teacher(name, msisdn, organization, token=token, groups=groups, email=email, password=password, username=username)
            except Exception, ex:
                request.POST.post_type=post_type
                logger.error("Error occurred while creating group:%s" % str(ex))
                errors.append("Error while saving data, please try again")
            else:
                #groups = get_groups(request.user, [organization])
                organizations = request.user.organization
                teachers = CustomUser.objects.filter(type=TEACHER, organization__in=organizations)
                groups = get_groups(request.user, organizations)
                for teacher in teachers:
                    teacher.groups = get_teacher_owner_group(teacher)
                message = "Teacher has been successfully created"
            return render(request, self.template_name, {"teachers": teachers, "errors": errors, "message": message, "groups":groups})



class OrganizationView(View):
    template_name='organization.html'

    def get(self, request):
        # <view logic>
        errors=[]
        try:
            organizations = Organization.objects.all()
        except Exception, ex:
            logger.error("Error occurred while getting organization")
            errors.append("Error while saving data")
        return render(request, self.template_name, {"errors":errors, "organizations": organizations})

    def post(self, request, id=None):
        errors=[]
        message=None
        post_type='post'
        if self.args:
            id=self.args[0]
            post_type='update'
        try:
            name = request.POST.get('name')
            country = request.POST.get('country')
            city = request.POST.get('city')
            state = request.POST.get('state')
            address = request.POST.get('address')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            errors.append("Required parameter was not there")
            #request.POST.set("post_type", post_type)
            request.POST.post_type = post_type
            return render(request, self.template_name, {'errors':errors})
        """if not name or not country or not city or not state or not address:
            errors.append("Required parameter was not there")
            #request.POST.set("post_type", post_type)
            request.POST.post_type = post_type
            return render(request, self.template_name, {'errors':errors})
        """
        organization=None
        if name and country and city and state and address:
            if id:
                # to handle update request
                try:
                    organization = Organization.objects.get(id=id)
                except Exception, ex:
                    logger.error("Organization does not exist :%s" % id)
                    errors.append("Error occurred while updating record, Please try again")
                else:
                    organization.name = name
                    organization.address = address
                    organization.city = city
                    organization.country = country
                    organization.state = state
                    organization.save()
                    message = "Organization has been successfully updated"
            else:
                # to handle create request
                try:
                    organization = Organization.objects.create(name=name, country=country, city=city, state=state, address=address)
                except Exception, ex:
                    #request.POST.set("post_type", post_type)
                    request.POST.post_type = post_type
                    logger.error("Error occurred while creating organization doc: %s, name: %s, country:%s, city: %s, state:%s, address:%s " % (str(ex), name, country, city, state, address))
                    errors.append("Error while saving data, please try again")
                else:
                    message = "Organization has been successfully created"
        else:
            errors.append("Required parameter was not there")
            #request.POST.set("post_type", post_type)
            request.POST.post_type = post_type
        organizations = Organization.objects.all()
        return render(request, self.template_name, {"errors": errors, "message": message, 'organization':organization, "organizations": organizations})
        #return render(request, self.template_name, {"organizations": organizations, "errors": errors, "message": message})

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        try:
            password =request.POST.get("password")
            password = 'CYOzgG27aAM='

            user = CustomUser.objects.get(username=request.POST.get('username'))
            if user.check_password('123'):
            #if user:
                user.backend = 'mongoengine.django.auth.MongoEngineBackend'
                login(request, user)
                request.session.set_expiry(60 * 60 * 1) # 1 hour timeout
                return HttpResponseRedirect('/dashboard/')
            else:
                return HttpResponse('login failed')
        except DoesNotExist:
            return HttpResponse('user does not exist')
        except Exception, ex:
            return HttpResponse('unknown error')
    return render(request, "login.html", {})

def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/login')

class SignUpView(View):
    template_name='signup.html'

    def get(self, request):
        # <view logic>
        return render(request, self.template_name, {})


