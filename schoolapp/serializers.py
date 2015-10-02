__author__ = 'ashish'
from rest_framework_mongoengine.serializers import DocumentSerializer
from schoolapp.models import Group, Organization, Attendance, User, Student
from rest_framework import serializers

class GroupSerializer(DocumentSerializer):

    class Meta:
        model = Group
        fields = ('name', 'organization', 'members', 'owner')

class OrganizationSerializer(DocumentSerializer):
    user = serializers.StringRelatedField(many=True)

    class Meta:
        model=Organization
        fields = ('name', 'city', 'state', 'country', 'user', 'address')


class UserSerializer(DocumentSerializer):
    group = serializers.StringRelatedField(many=True)

    class Meta:
        model=User
        fields = ('name', 'msisdn', 'devices', 'country', 'token', 'type', 'group', 'md', 'ts')

class UserLoginSerializer(DocumentSerializer):

    class Meta:
        model=User
        fields = ('msisdn', 'token', 'devices')

class AttendanceSerializer(DocumentSerializer):

    class Meta:
        model=Attendance
        fields = ('student', 'ts', 'present')

class StudentSerializer(DocumentSerializer):
    organization = serializers.StringRelatedField(many=True)

    class Meta:
        model=Student
        fields = ('name', 'roll_no', 'parents', 'group', 'organization')