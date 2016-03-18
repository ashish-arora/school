__author__ = 'ashish'
from rest_framework_mongoengine.serializers import DocumentSerializer
from schoolapp.models import Group, Organization, Attendance, CustomUser, Student, AttendanceSummary, Subjects, Status
from schoolapp.models import ProductPlan
from rest_framework import serializers

class GroupSerializer(DocumentSerializer):

    class Meta:
        model = Group
        fields = ('name', 'organization', 'members', 'owner')

class OrganizationSerializer(DocumentSerializer):

    class Meta:
        model=Organization
        fields = ('id', 'name', 'city', 'state', 'country', 'address')


class UserSerializer(DocumentSerializer):
    group = serializers.StringRelatedField(many=True)

    class Meta:
        model=CustomUser
        fields = ('first_name', 'last_name', 'msisdn', 'devices', 'country', 'token', 'type', 'group', 'md', 'ts', 'organization')

class UserLoginSerializer(DocumentSerializer):

    class Meta:
        model=CustomUser
        fields = ('username', 'password','devices')

class AttendanceSerializer(DocumentSerializer):

    class Meta:
        model=Attendance
        fields = ('student', 'ts', 'present')

class StudentSerializer(DocumentSerializer):
    organization = serializers.StringRelatedField(many=True)

    class Meta:
        model=Student
        fields = ('first_name', 'roll_no', 'parents', 'group', 'organization')



class UserDataSerializer(DocumentSerializer):

    class Meta:
        model=CustomUser
        exclude=("organization",)

class StudentDataSerializer(DocumentSerializer):

    parents = UserDataSerializer(many=True)

    class Meta:
        model=Student
        fields = ('first_name', 'roll_no', 'parents')

class GroupDataSerializer(DocumentSerializer):
    members = StudentDataSerializer(many=True)
    owner = UserDataSerializer(many=True)

    class Meta:
        model = Group
        #fields='__all_'

class OrganizationDataSerializer(DocumentSerializer):
    class Meta:
        model = Organization

class AttendanceDataSerializer(DocumentSerializer):
    class Meta:
        model = Attendance

class AttendanceSummaryDataSerializer(DocumentSerializer):
    class Meta:
        model = AttendanceSummary

class SubjectsDataSerializer(DocumentSerializer):
    class Meta:
        model = Subjects

class StatusDataSerializer(DocumentSerializer):
    class Meta:
        model = Status

class ProductPlanDataSerializer(DocumentSerializer):
    class Meta:
        model=ProductPlan

