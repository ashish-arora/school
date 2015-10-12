__author__ = 'ashish'
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout
from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.sites.models import get_current_site


def authenticate(username=None, password=None):
    try:
        user = User.objects.get(username=username,site__domain=settings.ROOT_SITE)
        if user.check_password(password):
            return user
    except User.DoesNotExist:
        return None
    except:
        return None

@login_required
def logout_then_redirect(request):
    user = request.user
    site = user.site
    try:
        logouturl = Property.objects.get(site=site, name='logouturl').value
        logout(request)
        response = HttpResponseRedirect('http://' + logouturl)
        response.delete_cookie('sivrloggedin')
        return response
    except:
        logout(request)
        if site.domain == settings.ROOT_SITE:
            response = HttpResponseRedirect('/sivr/')
        else:
            response = HttpResponseRedirect('/')
        response.delete_cookie('sivrloggedin')
        return response

@csrf_protect
@never_cache
def login(request, template_name='registration/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.REQUEST.get(redirect_field_name, '')

    if request.method == "POST":
        form = authentication_form(data=request.POST)
        if form.is_valid():
            netloc = urlparse.urlparse(redirect_to)[1]

            # Use default setting if redirect_to is empty
            if not redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL

            # Security check -- don't allow redirection to a different
            # host.
            elif netloc and netloc != request.get_host():
                redirect_to = settings.LOGIN_REDIRECT_URL

            if redirect_to == '/' and settings.SITE_DETECT.site.domain == settings.ROOT_SITE:
                redirect_to = '/sivr/'
            # Okay, security checks complete. Log the user in.
            auth_login(request, form.get_user())

            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()

            response = HttpResponseRedirect(redirect_to)
            exp_time = request.session.get_expiry_age()
            response.set_cookie('sivrloggedin', 'yes', exp_time)
            return response
    else:
        form = authentication_form(request)

    request.session.set_test_cookie()

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    context.update(extra_context or {})
    return render_to_response(template_name, context,
                              context_instance=RequestContext(request, current_app=current_app))