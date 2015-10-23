__author__ = 'ashish'
from django.views.generic import View
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
#from schoolapp.models import User
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, logout
from mongoengine.django.auth import User
from mongoengine.django.mongo_auth import models
from mongoengine.queryset import DoesNotExist
from schoolapp.models import *
import bson, base64, random, os
BASE64_URLSAFE="-_"
from schoolapp.utils import log
from forms import OrganizationForm
import json, time
from datetime import datetime, timedelta
from models import TEACHER, PARENT
from schoolapp.utils.helpers import *


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
                org = organization[0]
                if is_plan_within_expiry(org):
                    if can_add_student(org):
                        try:
                            create_student(first_name=first_name, last_name=last_name, roll_no=roll_no, group=grp, organization=org)
                        except Exception, ex:
                            #request.POST.set("post_type", post_type)
                            #request.POST.post_type = post_type
                            logger.error("Error occurred while creating Student doc: %s, first_name: %s, last_name:%s, roll_no: %s, class_value:%s" % (str(ex), first_name, last_name, roll_no,groupid ))
                            errors.append("Error while saving data, please try again")
                        else:
                            message = "Student profile has been successfully created"
                    else:
                        logger.error("free_students limit reached: %s"%(str(org.name)))
                        errors.append("Cannot add more students. Upgrade the plan for your Organization: %s"%(str(org.name)))
                else:
                    logger.error("Plan has expired for Organization: %s, on the date: %s"%(str(org.name)),str(get_plan_expiry(org).date()) )
                    errors.append("Plan has expired for your Organization: %s, on the date: %s"%(str(org.name)),str(get_plan_expiry(org).date()))
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
        group_id = request.POST.get('group_id')
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
                group.delete()
                message = "Group has been successfully deleted"
            except Exception, ex:
                logger.error("Error occurred while group deletion: %s" % id)
                errors.append("Error occurred while group deletion")
        data = get_group_list(request.user)
        data.update({"errors": errors, "message": message})
        return render(request, self.template_name, data)

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
        members=[]
        owners=[]
        subjects=[]
        if self.args:
            id=self.args[0]
            post_type='update'
        try:
            name = request.POST.get('name')
            organization_id = request.POST.get('organization_id')
            member_ids = request.POST.getlist('member_id[]')
            owner_ids = request.POST.getlist('owner_id[]')
            subject_ids = request.POST.getlist('subject_ids[]')
        except Exception, ex:
            logger.error("Error: %s" %(str(ex)))
            errors.append("Required parameter was not there")
            request.POST.post_type = post_type
            return render(request, self.template_name, {'errors':errors})
        if not name or not organization_id:
            errors.append("Required parameter was not there")
            request.POST.post_type = post_type
            return render(request, self.template_name, {'errors':errors})
        if member_ids:
            members = Student.objects.filter(id__in=member_ids)
        if owner_ids:
            owners = User.objects.filter(id__in=owner_ids)
        if subject_ids:
            subjects = Subjects.objects.filter(id__in=subject_ids)
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
                group=None
                groups=[]
                logger.error("Group does not exist :%s" % id)
                errors.append("Error occurred while updating record, Please try again")
            else:
                group.name = name
                group.organization = organization
                if members:
                    group.members=members
                if owners:
                    group.owner = owners
                if subjects:
                    group.subjects = subjects
                group.save()
                message = "Group has been successfully updated"
        else:
            # to handle create request
            try:
                group = Group.objects.create(name=name, organization=organization, members=members, owner=owners, subjects=subjects)
            except Exception, ex:
                request.POST.post_type = post_type
                logger.error("Error occurred while creating group:%s" % str(ex))
                errors.append("Error while saving data, please try again")
            else:
                message = "Group has been successfully created"
        groups = get_groups(request.user, [organization])
        organizations = request.user.organization
        owners = CustomUser.objects.filter(type=TEACHER, organization__in=request.user.organization)
        members = Student.objects.filter(organization__in=request.user.organization)
        return render(request, self.template_name, {"groups": groups, "errors": errors, "message": message, "owners":owners, "members":members, "organizations":organizations})

class TeacherDeleteView(View):
    template_name = 'teacher.html'

    def get(self, request, teacher_id):
        errors=[]
        message=None
        if teacher_id:
            try:
                teacher = CustomUser.objects.get(id=teacher_id)
                delete_teacher(teacher)
                message = "Teacher has been successfully deleted"
            except Exception, ex:
                logger.error("Error occurred while teacher deletion: %s" % id)
                errors.append("Error occurred while teacher deletion")
        data = get_teacher_view_data(request.user)
        data.update({"errors": errors, "message": message})
        return render(request, self.template_name, data)

class ParentsView(View):
    template_name='parents.html'

    def get(self, request):
        # <view logic>
        data = get_parent_view_data(request.user)
        return render(request, self.template_name, data)

    def post(self, request, id=None):
        errors=[]
        message=None
        post_type='post'
        if self.args:
            id=self.args[0]
            post_type='update'
        name = request.POST.get('name')
        msisdn = request.POST.get('msisdn')
        email = request.POST.get('email')
        username = request.POST.get('username')
        student_ids = request.POST.getlist("student_id[]")
        organization_id = request.POST.get('organization_id')
        password = request.POST.get('password')

        if not name or not student_ids or not msisdn or not username or not email or not organization_id:
            errors.append("Required parameter was not there")
        if not errors:
            try:
                organization = Organization.objects.get(id=organization_id)
            except Exception, ex:
                errors.append("Organization does not exist")
                logger.error("Organization does not exist: %s" % organization_id)
        if not errors:
            students = Student.objects.filter(id__in=student_ids)
            if id:
                # to handle update request
                try:
                    parent = CustomUser.objects.get(id=id)
                    update_parent(parent, name, msisdn, organization, type=PARENT, students=students, email=email, password=password)
                except Exception, ex:
                    logger.error("Error occurred while updating parent for id : %s error:%s" % (id, str(ex)))
                    errors.append("Error occurred while updating record, Please try again")
                else:
                    message = "Parent has been successfully updated"
            else:
                # to handle create request
                try:
                    token = base64.urlsafe_b64encode(os.urandom(8))
                    create_parent(name, msisdn, organization, token=token, students=students, email=email, password=password, username=username)
                except Exception, ex:
                    request.POST.post_type=post_type
                    logger.error("Error occurred while creating parent:%s" % str(ex))
                    errors.append("Error while saving data, please try again")
                else:
                    message = "Parent has been successfully created"
        request.POST.post_type = post_type
        data = get_parent_view_data(request.user)
        data.update({"errors": errors, "message": message})
        return render(request, self.template_name, data)

class ParentsDeleteView(View):
    template_name = 'parents.html'

    def get(self, request, parent_id):
        errors=[]
        message=None
        if parent_id:
            try:
                parent = CustomUser.objects.get(id=parent_id)
                delete_parent(parent)
                message = "Parent has been successfully deleted"
            except Exception, ex:
                logger.error("Error occurred while parent deletion: %s" % id)
                errors.append("Error occurred while parent deletion")
        data = get_parent_view_data(request.user)
        data.update({"errors": errors, "message": message})
        return render(request, self.template_name, data)


class TeacherView(View):
    template_name='teacher.html'

    def get(self, request, message='', errors=[]):
        # <view logic>
        data = get_teacher_view_data(request.user)
        data.update({"message":message, "errors":errors})
        return render(request, self.template_name, data)

    def post(self, request, id=None):
        errors=[]
        message=None
        post_type='post'
        if self.args:
            id=self.args[0]
            post_type='update'
        name = request.POST.get('name')
        msisdn = request.POST.get('msisdn')
        email = request.POST.get('email')
        username = request.POST.get('username')
        group_ids = request.POST.getlist("group_id[]")
        organization_id = request.POST.get('organization_id')
        password = request.POST.get('password')
        if not name or not group_ids or not msisdn or not username or not email or not organization_id:
            errors.append("Required parameter was not there")
            request.POST.post_type = post_type
        groups = Group.objects.filter(id__in=group_ids)
        try:
            organization = Organization.objects.get(id=organization_id)
        except Exception, ex:
            errors.append("Organization does not exist")
            logger.error("Organization does not exist: %s" % organization_id)
        if not errors:
            teachers=[]
            if id:
                # to handle update request
                try:
                    teacher = CustomUser.objects.get(id=id)
                    update_teacher(teacher, name, msisdn, organization, type=TEACHER, groups=groups, email=email, password=password)
                except Exception, ex:
                    logger.error("Error occurred while updating teacher for id :%s error:%s" % (id, str(ex)))
                    errors.append("Error occurred while updating record, Please try again")
                else:
                    message = "Teacher has been successfully updated"
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
                    message = "Teacher has been successfully created"
        request.POST.post_type = post_type
        data = get_teacher_view_data(request.user)
        data.update({"errors":errors, "message":message})
        return render(request, self.template_name, data)



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
    redirect_to = request.GET.get('next')
    if request.method == "POST":
        try:
            password =request.POST.get("password")
            user = CustomUser.objects.get(username=request.POST.get('username'))
            if user.check_password(password):
                user.backend = 'mongoengine.django.auth.MongoEngineBackend'
                login(request, user)
                request.session.set_expiry(60 * 60 * 1) # 1 hour timeout
                if redirect_to:
                    return HttpResponseRedirect(redirect_to)
                return HttpResponseRedirect('/dashboard/')
            else:
                return HttpResponse('login failed')
        except DoesNotExist:
            return HttpResponse('user does not exist')
        except Exception, ex:
            return HttpResponse('unknown error')
    app_path=request.get_full_path()
    return render(request, "login.html", {"app_path":app_path})

def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/login')

class SignUpView(View):
    template_name='signup.html'

    def get(self, request):
        # <view logic>
        return render(request, self.template_name, {})

class AttendanceView(View):
    template_name='attendance.html'

    def get(self, request):
        data = get_attendance_data(request.user)
        return render(request, self.template_name, data)

    def post(self, request):
        errors=[]
        message=""
        group_id = request.POST.get('group_id')
        date_selected = request.POST.get('date')
        student_ids = request.POST.getlist('student_ids[]')
        if not group_id or not date_selected or not student_ids:
            errors.append("Required Parameter is not there")
        now = datetime.now()
        today = now.date()
        next_day  = today + timedelta(days=1)
        start = int(time.mktime(today.timetuple()))
        end = int(time.mktime(next_day.timetuple()))
        show_attendance=True
        if not errors:
            group = Group.objects.get(id=group_id)
            attendances = AttendanceSummary.objects.filter(group=group, ts__gte=start, ts__lte=end)
            if attendances:
                message="Attendance already happened for the day"
                show_attendance=False
            else:
                students_present=[]
                students_absent=[]
                students = Student.objects.filter(group=group)
                for student in students:
                    if str(student.id) in student_ids:
                        students_present.append(student)
                    else:
                        students_absent.append(student)
                epoch_time = int(time.time())
                attendance_doc=[]
                present_count, absent_count=0,0
                for student in students_present:
                    attendance_doc.append(Attendance(student=student, present=1, ts=epoch_time))
                    present_count+=1
                for student in students_absent:
                    attendance_doc.append(Attendance(student=student, present=0, ts=epoch_time))
                    absent_count+=1
                try:
                    Attendance.objects.insert(attendance_doc)
                    AttendanceSummary.objects.create(group=group, present=present_count, absent=absent_count, ts=epoch_time)
                except Exception, ex:
                    logger.error("Error occurred while saving attendance for group_id: %s, student_ids :%s, error:%s" %(group_id, student_ids, str(ex)))
                    errors.append("Error occurred while saving attendance, Please try again")
                else:
                    message="Attendance has been successfully submitted"
        data = get_attendance_data(request.user)
        data.update({"show_attendance":show_attendance, "message":message, "errors":errors})
        return render(request, self.template_name, data)

class WebSiteView(View):
    template_name='single_page.html'

    def get(self, request):
        # <view logic>

        return render(request, self.template_name)


class NewLoginView(View):
    template_name='new_login.html'

    def get(self, request):
        # <view logic>

        return render(request, self.template_name)

class NewSignUpView(View):
    template_name='new_signup.html'

    def get(self, request):
        # <view logic>

        return render(request, self.template_name)


class SignUpTeacherView(View):
    template_name='new_signup_teacher.html'

    def get(self, request):
        # <view logic>

        return render(request, self.template_name)

class SignUpParentView(View):
    template_name='new_signup_parent.html'

    def get(self, request):
        # <view logic>

        return render(request, self.template_name)

class EventsView(View):
    template_name='events.html'

    def get(self, request):
        # <view logic>
        status_list = get_events_list(request.user)
        return render(request, self.template_name, {"status_list":status_list})

    def post(self, request):
        image_body=None
        message = None
        errors=[]
        file = self.request.FILES.get('file')

        if file:
            image_body  = file.read()
        status = self.request.POST.get('message')

        if not image_body and not status:
            errors.append("Please specify either message or attached file")
        try:
            to_users = get_to_users(request.user)
            status_obj = post_status(request.user, data=image_body, message=status, to_users=to_users)
        except Exception, ex:
            logger.error("Error occurred while posting status update: user_id: %s, error: %s" % (request.user.id, str(ex)))
            errors.append("Error occurred while doing status update")
        else:
            message="Status has been posted successfully"
        status_list = get_events_list(request.user)
        return render(request, self.template_name, {"errors":errors, "message":message, "status_list":status_list})

class ProfileView(View):
    template_name = 'profile.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        errors=[]
        message=None
        user = request.user
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        msisdn = request.POST.get('msisdn')

        if not first_name or not last_name or not email or not msisdn:
            errors.append("Please specify all the fields")

        if not valid_msisdn(msisdn):
            errors.append("Phone Number is not it valid format")

        if not valid_email(email):
            errors.append("Email is not it valid format")

        if not errors:
            user.first_name= first_name
            user.last_name = last_name
            user.msisdn=msisdn
            user.email= email
            user.save()
            message="You have successfully updated the user info"
        return render(request, self.template_name, {"errors":errors, "message":message})


class AvatarView(View):
    template_name = 'profile.html'

    def post(self, request):
        image_body=None
        message = None
        errors=[]
        file = self.request.FILES.get('file')

        if file:
            image_body = file.read()

        if not image_body:
            errors.append("Please select the image")

        if not errors:
            try:
                to_users = get_to_users(request.user)
                status_obj = post_status(request.user, data=image_body, message='', to_users=to_users, profile_pic=True)
            except Exception, ex:
                logger.error("Error occurred while posting profile pic update: user_id: %s, error: %s" % (request.user.id, str(ex)))
                errors.append("Error occurred while doing profile pic update")
            else:
                message="Profile Pic has been updated successfully"
        return render(request, self.template_name, {"errors":errors, "message":message})

class SubjectsView(View):
    template_name='subjects.html'

    def get(self, request):
        subjects = Subjects.objects.all(organization__in = request.user.organization)
        return render(request, self.template_name, {"subjects": subjects})

    def post(self, request, subject_id=None):
        errors=[]
        message=""
        post_type='post'
        if self.args:
            subject_id=self.args[0]
            post_type='update'
        organization_id = request.POST.get('organization_id')
        subject_name = request.POST.get('subject_name')
        if not organization_id or not subject_name:
            errors.append("Required Parameter is not there")
        if not errors:
            try:
                if id:
                    edit_subject(id=subject_id, name=subject_name, organization_id=organization_id)
                else:
                    create_subject(name=subject_name, organization_id=organization_id)
            except Exception, ex:
                logger.error("Error occurred while posting subjects: user_id: %s, error: %s" % (request.user.id, str(ex)))
                errors.append("Error occurred while doing subjects update")
        else:
            message="Status has been posted successfully"
        subjects = get_subjects_list(request.user)
        return render(request, self.template_name, {"errors":errors, "message":message, "subjects": subjects})

class SubjectsDeleteView(View):
    template_name='subjects.html'

    def get(self, request, subject_id):
        errors=[]
        message=None
        if subject_id:
            try:
                delete_subject(request.user, subject_id)
                message = "Subject has been successfully deleted"
            except Exception, ex:
                logger.error("Error occurred while subject deletion: %s" % id)
                errors.append("Error occurred while subject deletion")
        subjects = get_subjects_list(request.user)
        subjects.update({"errors": errors, "message": message})
        return render(request, self.template_name, subjects)


class HomeWorkView(View):
    template_name='homework.html'

    def get(self, request, group_id):
        errors=[]
        message=''
        date = request.GET.get("date","")
        if group_id:
            try:
                homework_list = get_homework(request.user, group_id, date=date)
            except Exception, ex:
                logger.error("Error occurred while getting homework error: %s" % str(ex))
                errors.append("Error occurred while getting homework")
        else:
            errors.append("Please specify the group id")
        homework_list.update({"errors": errors, "message": message})
        return render(request, self.template_name, homework_list)

    def post(self, request):
        errors=[]
        message=None
        user = request.user
        group_id = request.POST.get('group_id')
        text = request.POST.get('text')
        subject_id = request.POST.get('subject_id')

        if not group_id or not text or not subject_id:
            errors.append("Please specify all the fields")

        if not errors:
            try:
                post_home_work(user, group_id, subject_id, text)
                homework_list = get_homework(request.user, group_id)
            except Exception, ex:
                logger.error("Error occurred while posting homework error : %s" % str(ex))
                errors.append("Error occurred while posting homework")
            else:
                message="Homwork has been successfully posted"
        homework_list.update({"errors": errors, "message": message})
        return render(request, self.template_name, homework_list)









