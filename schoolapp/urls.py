__author__ = 'ashish'
from django.conf.urls import patterns, include, url

from django.contrib import admin
#admin.autodiscover()
from schoolapp import views, web_views

from django.conf.urls import url, include
from schoolapp.models import User
from rest_framework import routers, serializers, viewsets
from django.contrib.auth.decorators import login_required

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
    url(r'^api/v1/organization/delete', views.OrganizationDeleteView.as_view()),
    url(r'^api/v1/organization', views.OrganizationView.as_view()),
    url(r'^api/v1/student/delete', views.StudentDeleteView.as_view()),
    url(r'^api/v1/group', views.GroupView.as_view()),
    url(r'^api/v1/ping',views.PingWebHandler.as_view()),
    url(r'^api/v1/pin', views.AccountPinValidation.as_view()),
    url(r'^login/', web_views.login_view),
    url(r'^logout/', web_views.logout_view),
    url(r'^signup/', web_views.SignUpView.as_view()),
    url(r'^index/', views.IndexView.as_view()),

    url(r'^dashboard/blank/', views.DashboardBlankView.as_view()),
    url(r'^dashboard/bootel/', views.DashboardBootElView.as_view()),
    url(r'^dashboard/bootgrid/', views.DashboardBootGridView.as_view()),
    url(r'^dashboard/charts/', views.DashboardChartsView.as_view()),
    url(r'^dashboard/forms/', views.DashboardFormsView.as_view()),
    url(r'^dashboard/rtl/', views.DashboardRtlView.as_view()),
    url(r'^dashboard/tables/', views.DashboardTablesView.as_view()),
    url(r'^student/(.*)/', login_required(web_views.StudentView.as_view(), login_url='/login/')),
    url(r'^student/', login_required(web_views.StudentView.as_view(), login_url='/login/')),
    url(r'^teacher/', web_views.TeacherView.as_view()),
    url(r'^organization/(.*)/', login_required(web_views.OrganizationView.as_view(), login_url='/login/')),
    url(r'^organization/', login_required(web_views.OrganizationView.as_view(), login_url='/login/')),
    url(r'^group/(.*)/', login_required(web_views.GroupView.as_view(), login_url='/login/')),
    url(r'^group/', login_required(web_views.GroupView.as_view(), login_url='/login/')),
    url(r'^group/delete/', login_required(web_views.GroupDeleteView.as_view(), login_url='/login/')),
    url(r'^manageuser/teacher/delete/(.*)/', login_required(web_views.TeacherDeleteView.as_view(), login_url='/login/')),
    url(r'^manageuser/teacher/(.*)/', login_required(web_views.TeacherView.as_view(), login_url='/login/')),
    url(r'^manageuser/teacher', login_required(web_views.TeacherView.as_view(), login_url='/login/'), name="teacher_view"),
    url(r'^manageuser/parent/delete/(.*)/', login_required(web_views.ParentsDeleteView.as_view(), login_url='/login/')),
    url(r'^manageuser/parent/(.*)/', login_required(web_views.ParentsView.as_view(), login_url='/login/')),
    url(r'^manageuser/parent', login_required(web_views.ParentsView.as_view(), login_url='/login/')),
    url(r'^home/', web_views.WebSiteView.as_view()),

    url(r'^attendance/', login_required(web_views.AttendanceView.as_view(), login_url='/login/')),

    url(r'^dashboard/', login_required(views.DashboardView.as_view(), login_url='/login/')),


    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^docs/', include('rest_framework_swagger.urls')),
)
