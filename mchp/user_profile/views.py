from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.shortcuts import redirect,render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.views.generic.detail import DetailView
from django.views.generic.edit import View
from django.http import HttpResponse, HttpResponseGone
from django.utils.decorators import method_decorator
# from django.views.decorators.csrf import ensure_csrf_cookie

from allauth.account.decorators import verified_email_required
from allauth.account.models import EmailAddress
from allauth.account.adapter import get_adapter

from calendar_mchp.models import ClassCalendar, CalendarEvent
from schedule.models import School, Major, SchoolEmail, Course
from user_profile.models import Student, OneTimeFlag, OneTimeEvent
from documents.models import Document
from lib.decorators import school_required
from referral.models import ReferralCode, Referral

import json
import logging
import magic
logger = logging.getLogger(__name__)

'''
url: /profile/<number>/slug
url: /profile/<number>
url: /profile/
name: profile
name: my_profile
'''
class ProfileView(DetailView):
    template_name = 'user_profile/profile.html'
    model = Student

    def get_object(self):
        if 'number' in self.kwargs:
            # url: /profile/<number>/
            return get_object_or_404(self.model, id=self.kwargs['number'])
        else:
            # url: /profile/ (logged in users account)
            return get_object_or_404(self.model, user=self.request.user)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        context = super(ProfileView, self).get_context_data(**kwargs)
        context['profile'] = self.object.profile
        context['viewer'] = self.viewer
        docs = Document.objects.filter(
            owner = self.object
        ).order_by('create_date')[:10]
        context['upload_list'] = docs
        cals = ClassCalendar.objects.filter(
            owner = self.object,
            private=False,
        ).select_related()
        context['calendars'] = cals
        
        for cal in cals:
            total_count = CalendarEvent.objects.filter(
                calendar=cal
            ).count()
            setattr(cal, 'events', total_count)

        all_counts = len(cals) + len(docs)
        if all_counts == 0:
            all_counts = 1
        context['cal_percent'] = (len(cals) * 100) / all_counts
        context['doc_percent'] = (len(docs) * 100) / all_counts
        context['common'] = Course.objects.get_classes_in_common(self.viewer, self.object)

        return context

    @method_decorator(school_required)
    def dispatch(self, *args, **kwargs):
        self.viewer = self.request.user.student
        return super(ProfileView, self).dispatch(*args, **kwargs)

profile = ProfileView.as_view()

'''
url: /accounts/settings/
name: account_settings
'''
class AccountSettingsView(View):
    template_name = 'user_profile/account_settings.html'

    def get(self, request, *args, **kwargs):
        ref = ReferralCode.objects.get_referral_code(request.user)
        data = {
            'referral_code': ref.referral_code,
            'referral_link': ref.referral_link,
            'referral_reward': settings.MCHP_PRICING['referral_reward'],
        }
        return render(request, self.template_name, data)

    @method_decorator(school_required)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(AccountSettingsView, self).dispatch(*args, **kwargs)

account_settings = AccountSettingsView.as_view()

'''
url: /profile/notifications/
name: notifications
'''
class NotificationsView(View):
    template_name = 'user_profile/notifications.html'

    def get(self, request, *args, **kwargs):
        data = {
        }
        return render(request, self.template_name, data)

    @method_decorator(school_required)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(NotificationsView, self).dispatch(*args, **kwargs)

notifications = NotificationsView.as_view()

'''
url: /profile/migrate-user/
name: migrate_user
'''
class MigrateUserView(View):
    template_name = 'user_profile/migrate_user.html'

    # uggg
    def get(self, request, *args, **kwargs):
        email = request.session.pop('email', None)
        request.session.flush()
        if not email:
            return render(request, self.template_name, {})
        from allauth.account.forms import ResetPasswordForm
        form = ResetPasswordForm()
        cleaned_data = {
            'email': email
        }
        setattr(form, 'cleaned_data', cleaned_data)
        form.clean_email()
        form.save()
        data = {
            'email': email,
        }
        return render(request, self.template_name, data)

    def dispatch(self, *args, **kwargs):
        return super(MigrateUserView, self).dispatch(*args, **kwargs)

migrate_user = MigrateUserView.as_view()

'''
url: /profile/confirm-school/
name: confirm_school
'''
class ConfirmSchoolView(View):
    template_name = 'user_profile/school.html'

    def get(self, request, *args, **kwargs):
        # clear out the migration session info
        request.session.pop('migration', None)

        all_schools = School.objects.all().values('name', 'domain', 'pk').order_by('name')
        next = request.GET.get('next', '')
        data = {
            'next': next,
            'schools': all_schools,
        }
        # try to find their email domain in the db
        email = request.user.email.split('@')[1].lower()
        school_email = SchoolEmail.objects.filter(
            email_domain = email
        )
        guess_school = None

        # we found it, maybe!
        if school_email.exists():
            school_email = school_email[0]
            guess_school = school_email.school
        else:
            # add this domain to the db for later manual curation
            SchoolEmail.objects.create(
                email_domain = email
            )

        # just because we found the email domain, doesn't mean we know the school yet
        # the school could still be null in the db 
        if guess_school:
            data['guess_school'] = guess_school
        else:
            # try to match the school based on the schools site domain
            guess_school = School.objects.get(pk=1)
            email_parts = email.split('.')[:-1]
            for part in email_parts:
                if part == 'email':
                    continue
                schools = School.objects.filter(domain__icontains=part)
                if schools.exists():
                    guess_school = schools[0]
                    break
            data['guess_school'] = guess_school

        return render(request, self.template_name, data)

    def post(self, request, *args, **kwargs):
        school = request.POST.get('school', '')
        grade_level = request.POST.get('grade_level', None)
        school = School.objects.get(pk=school)
        try:
            student = request.user.student 
            student.school = school
            student.grade_level = grade_level
            student.save()
            return redirect(reverse('dashboard'))
        except Student.DoesNotExist:
            student = Student.objects.create_student(request.user, school)
            if grade_level:
                student.grade_level = grade_level
                student.save()

        # referral stuff
        ref = request.session.get('referrer', '')
        if ref:
            referrer = User.objects.get(pk=ref)
            Referral.objects.refer_user(request.user, referrer, Student.objects.referral_reward)

        next = request.POST.get('next', reverse('course_add'))
        next = reverse('course_add')
        return redirect(next)

    @method_decorator(verified_email_required)
    def dispatch(self, *args, **kwargs):
        return super(ConfirmSchoolView, self).dispatch(*args, **kwargs)

confirm_school = ConfirmSchoolView.as_view()

@require_POST
def get_email(request):
    email = request.POST["email"]
    if request.is_ajax():
        if 'initial_email' in request.session:
            return HttpResponseGone(json.dumps({'message': 'initial_email already set'}), content_type='application/javascript')
        else:
            request.session['initial_email'] = email
            return HttpResponse(json.dumps({}), content_type='application/javascript')
    else:
        request.session['initial_email'] = email
        return redirect('/accounts/signup')

@require_POST
def resend_email(request):
    if request.is_ajax():
        email = request.POST["email"]
        try:
            email_address = EmailAddress.objects.get(email=email)
            get_adapter().add_message(request,
                                      messages.INFO,
                                      'account/messages/'
                                      'email_confirmation_sent.txt',
                                      {'email': email})
            email_address.send_confirmation(request)
        except EmailAddress.DoesNotExist:
            return HttpResponseGone(json.dumps({}), content_type='application/javascript')
        return HttpResponse(json.dumps({}), content_type='application/javascript')
    else:
        return redirect('/')

class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.

    I stole this right from the django website.
    """
    def render_to_json_response(self, context, **response_kwargs):
        data = json.dumps(context)
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)

    def ajax_messages(self):
        django_messages = []

        for message in messages.get_messages(self.request):
            django_messages.append({
                "level": message.level,
                "message": message.message,
                "extra_tags": message.tags,
            })
        return django_messages

'''
url: /profile/edit-pic/
name: edit_pic
'''
class PicView(View, AjaxableResponseMixin):
    def post(self, request, *args, **kwargs):
        print(request.FILES)
        if request.is_ajax():
            pic = request.FILES.get('pic')
            if self._check_pic(pic):
                profile = request.user.student.profile
                # Pass false so FileField doesn't save the model.
                if profile.pic:
                    profile.pic.delete(False)

                # save the new pic
                profile.pic = pic
                profile.save()
                data = {
                    'url': profile.pic.url
                }
            else:
                return self.render_to_json_response('Unsupported filetype', status=403)
            return self.render_to_json_response(data, status=200)
        else:
            return redirect(reverse('my_profile'))

    def get(self, request, *args, **kwargs):
        return redirect(reverse('my_profile'))

    def _check_pic(self, pic):
        filetypes = [b'image/jpeg', b'image/png', b'image/gif',]

        chunk = pic.file.read(1024)
        filetype = magic.from_buffer(chunk, mime=True)
        pic.file.seek(0,0)
        return filetype in filetypes

edit_pic = PicView.as_view()

'''
url: /profile/edit-username/
name: edit_username
'''
class UsernameView(View, AjaxableResponseMixin):
    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            username = request.POST.get('value', '')[:30]
            request.user.username = username
            # respect blacklisted username from all auth settings
            from allauth.account import app_settings
            username_blacklist_lower = [ub.lower() for ub in app_settings.USERNAME_BLACKLIST]
            if username.lower() in username_blacklist_lower:
                return self.render_to_json_response({'error': 'You can not use that name'}, status=403)
            try:
                request.user.save()
            except IntegrityError:
                return self.render_to_json_response({'error': 'Someone already has that username.'}, status=400)
            return self.render_to_json_response({'username': username}, status=200)
        else:
            return redirect(reverse('my_profile'))

    def get(self, request, *args, **kwargs):
        return redirect(reverse('my_profile'))

edit_username = UsernameView.as_view()

'''
url: /profile/edit-blurb/
name: edit_blurb
'''
class BlurbView(View, AjaxableResponseMixin):
    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            profile = request.user.student.profile
            profile.blurb = request.POST.get('value', '')[:200]
            profile.save()
            return self.render_to_json_response({}, status=200)
        else:
            return redirect(reverse('my_profile'))

    def get(self, request, *args, **kwargs):
        return redirect(reverse('my_profile'))

edit_blurb = BlurbView.as_view()

'''
url: /profile/edit-major/
name: edit_major
'''
class MajorView(View, AjaxableResponseMixin):
    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            major_str = request.POST.get('value', '')
            self.student = request.user.student
            major = Major.objects.filter(
                name=major_str,
            )
            if not major.exists():
                major = Major.objects.filter(
                    name__icontains=major_str
                )
            if major.exists():
                self.student.major = major[0]
                self.student.save()
                return self.render_to_json_response({}, status=200)
            else:
                return self.render_to_json_response('We couldn\'t find that major! Try picking something less esoteric', status=403)
        else:
            return redirect(reverse('my_profile'))

    def get(self, request, *args, **kwargs):
        return redirect(reverse('my_profile'))

edit_major = MajorView.as_view()

'''
url: /profile/toggle-flag/
name: toggle_flag
'''
class ToggleFlag(View, AjaxableResponseMixin):
    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            if request.user.is_authenticated():
                event_name = request.POST.get('event', '')
                event = OneTimeEvent.objects.get_event(event_name)
                if not event:
                    data = {
                        'error': '{} is not a valid event'.format(event_name)
                    }
                    return self.render_to_json_response(data, status=400)

                OneTimeFlag.objects.set_flag(request.user.student, event)
                return self.render_to_json_response({}, status=200)
             else:
                return redirect(reverse('my_profile'))
        else:
            return redirect(reverse('my_profile'))

    def get(self, request, *args, **kwargs):
        return redirect(reverse('my_profile'))

toggle_flag = ToggleFlag.as_view()

'''
url: /profile/confirmed/
name: account_confirmed
'''
class EmailConfirmedView(View, AjaxableResponseMixin):
    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            address = request.GET.get('email', None)
            email = EmailAddress.objects.filter(
               email=address 
            )
            if not email.exists():
                return self.render_to_json_response({}, status=404)
            else:
                email = email[0]
            confirmed = email.verified
            return self.render_to_json_response({'confirmed': confirmed}, status=200)
        else:
            return redirect(reverse('my_profile'))

account_confirmed = EmailConfirmedView.as_view()
