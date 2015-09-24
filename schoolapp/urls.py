__author__ = 'ashish'
from django.conf.urls import patterns, include, url

from django.contrib import admin
#admin.autodiscover()
from schoolapp import views

from django.conf.urls import url, include
from schoolapp.models import User
from rest_framework import routers, serializers, viewsets

# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')

# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
#router.register(r'users', UserViewSet)

urlpatterns = patterns('',
    url(r'^', include(router.urls)),
    url(r'^api/v1/account/signup', views.AccountSignUp.as_view()),
    url(r'^api/v1/account/login', views.AccountLogin.as_view()),
    url(r'^api/v1/attendance', views.Attendance.as_view()),
    url(r'^api/v1/organization', views.OrganizationView.as_view()),
    url(r'^api/v1/group', views.GroupView.as_view()),
    url(r'^api/v1/pin', views.AccountPinValidation.as_view()),

    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^docs/', include('rest_framework_swagger.urls')),
)
