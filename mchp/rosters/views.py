from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse_lazy
from django.db import IntegrityError
from django.views.generic import FormView, UpdateView, ListView
from django.utils.decorators import method_decorator
from lib.decorators import school_required
from documents.exceptions import DuplicateFileError
from django.contrib import messages
from documents.models import Document, DocumentPurchase
from django.forms.formsets import formset_factory
from django.http import HttpResponse, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404, redirect

from schedule.models import Course
from . import forms, models, utils

from lib.decorators import intern_manager_required, rep_required
from rosters.tasks import extract_roster
from notification.api import add_notification


class RosterSubmitView(FormView):
    """ Submit a new roster.

    Notes
    -----
    [TODO] this should ensure user is rep/intern

    """
    template_name = 'rosters/roster_submit_form.html'
    form_class = forms.RosterSubmitForm
    success_url = reverse_lazy('roster-upload')

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        eventset = forms.RosterEventFormSet(request.POST)

        # print (eventset)

        if form.is_valid():
            form.cleaned_data['events'] = eventset
            return self.form_valid(form)
        else:
            return self.form_invalid(form, **kwargs)

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        course_id = form.cleaned_data['course']
        course_name = form.cleaned_data['course_name']
        roster_html = form.cleaned_data['roster_html']

        if len(form.cleaned_data['emails']) > 3:
            instructor_emails = form.cleaned_data['emails'].split()
        else:
            messages.error(
                self.request,
                'Class Set rejected: no or invalid instructor email(s)'
            )
            return self.get(self.request)

        document = form.cleaned_data['document']
        events = form.cleaned_data['events']

        course = Course.objects.get(pk=course_id)

        params = {
            'roster_html': roster_html,
            'instructor_emails': instructor_emails,
            'created_by': self.request.user.student_user,
            'course': course
        }

        roster = models.Roster.objects.create(**params)

        if events.is_valid():
            for event in events.cleaned_data:
                print (event)
                if 'title' in event:
                    params = {
                        'title': event['title'],
                        'date': event['date'],
                        'roster': roster
                    }
                    models.RosterEventEntry.objects.create(**params)


        # create roster entries
        if len(instructor_emails) > 0:
            for email in instructor_emails:
                params = {
                    'email': email,  # utils.preprocess_email(email),
                    'roster': roster,
                    'approved': False
                }
                try:
                    user = utils.get_user(email)
                    if user is not None and hasattr(user, 'profile_user'):
                        params['profile'] = user.profile_user
                    models.RosterInstructorEntry.objects.create(**params)
                except ValidationError:
                    roster.delete()
                    messages.error(
                        self.request,
                        'Class Set rejected: no or invalid instructor email(s)'
                    )
                    return self.get(self.request)

        else:
            roster.delete()
            messages.error(
                self.request,
                'Class Set rejected: no instructor email(s)'
            )
            return self.get(self.request)


        try:
            doc = Document(type=Document.SYLLABUS, title='Course Syllabus for ' + course.name,
                           description='Course Syllabus for ' + course.name,
                           document=document, price=0, course_id=None, approved=False, roster=roster, owner=self.request.user.student)
            doc.save()
        except DuplicateFileError as err:
            roster.delete()
            messages.error(
                self.request,
                'Class Set rejected: syllabus is a duplicate'
            )
            return self.get(self.request)

        try:
            extract_roster(roster)
        except IntegrityError:
            doc.delete()
            roster.delete()

            messages.error(
                self.request,
                'Class Set rejected: roster is invalid or a duplicate'
            )
            return self.get(self.request)

        messages.success(
            self.request,
            "Class Set for {} was submitted and is now under review".format(roster.course)
        )

        add_notification(
            self.request.user,
            'Your Class Set for {} is under review'.format(roster.course)
        )

        return super().form_valid(form)

    @method_decorator(school_required)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super().dispatch(*args, **kwargs)


class RosterReviewView(UpdateView):
    """ Review a submitted roster.

    Notes
    -----
    As with the submit view, this should verify permissions.

    """
    model = models.Roster
    fields = ['status']
    template_name_suffix = '_review_form'

    # TODO: implement document_uploaded signal for syllabus upon doc approval

    def get_success_url(self):
        return reverse_lazy('roster-review', args=[self.object.pk])

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context['course'] = self.get_object().course
    #     return context

    @method_decorator(intern_manager_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class RosterListView(ListView):
    """ List rosters

    Notes
    -----
    As with the submit view, this should verify permissions.

    """
    model = models.Roster
    #fields = ['status']
    template_name_suffix = '_list'
    #template_name = 'rosters/staff-intern-prototype.html'
#    paginate_by = 25

    def post(self, request, *args, **kwargs):
        roster_id = request.POST['hidden_roster_id']
        action = request.POST['hidden_roster_action']

        roster = models.Roster.objects.get(pk=roster_id)
        if action == 'reject':
            from rosters.signals import roster_rejected
            roster_rejected.send(sender=self.__class__, roster=roster)

        if action == 'approve':
            from rosters.signals import roster_approved
            roster_approved.send(sender=self.__class__, roster=roster)

        if action == 'extract':
            print ('re-extracting')
            extract_roster(roster)

        if action == 'delete':
            roster.delete()


        return redirect(reverse('roster-list'))

    def get_context_data(self, **kwargs):
            context = super(RosterListView, self).get_context_data(**kwargs)
            context['rosters'] = models.Roster.objects.all()

            return context

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context['course'] = self.get_object().course
    #     return context

    @method_decorator(intern_manager_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

