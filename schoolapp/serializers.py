__author__ = 'ashish'
from rest_framework_mongoengine.serializers import DocumentSerializer
from schoolapp.models import Group, Organization, Attendance, User

class GroupSerializer(DocumentSerializer):

    class Meta:
        model = Group
        fields = ('name', 'organization_id', 'members')

class OrganizationSerializer(DocumentSerializer):

    class Meta:
        model=Organization
        fields = ('name', 'city', 'state', 'country', 'address')


class UserSerializer(DocumentSerializer):

    class Meta:
        model=User
        fields = ('name', 'msisdn', 'devices', 'country', 'token', 'type', 'organization', 'parent_id', 'md', 'groups', 'ts')

class AttendanceSerializer(DocumentSerializer):

    class Meta:
        model=Attendance
        fields = ('student', 'present', 'ts')