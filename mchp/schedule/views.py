from allauth.account.decorators import verified_email_required
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic.edit import FormView 
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.template import Context
from django.db.models import Count
# from django.http import HttpResponseNotAllowed, HttpResponse
from django.http import HttpResponse

from schedule.forms import CourseCreateForm, CourseChangeForm, CourseSearchForm
from schedule.models import Course

import logging
import json
logger = logging.getLogger(__name__)

# most views should inherit from this if they submit form data
class _BaseCourseView(FormView):

    def get_success_url(self):
        # Redirect to previous url - security of getting referer this way?
        return self.request.META.get('HTTP_REFERER', None)

    def form_invalid(self, form):
        return super(_BaseCourseView, self).form_invalid(form)

    # dispatch takes care of calling default get and post functions
    # and the decorator will happen in every subclass that doens't override
    @method_decorator(verified_email_required)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(_BaseCourseView, self).dispatch(*args, **kwargs)

class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)

    I stole this right from the django website, it could be used on other views
    as well as.
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

    def form_invalid(self, form):
        response = super(AjaxableResponseMixin, self).form_invalid(form)
        if self.request.is_ajax():
            return self.render_to_json_response(form.errors, status=400)
        else:
            return response

    def form_valid(self, form):
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super(AjaxableResponseMixin, self).form_valid(form)
        if self.request.is_ajax():
            data = {
                'pk': self.object.pk,
            }
            return self.render_to_json_response(data)
        else:
            return response

class CourseCreateView(_BaseCourseView):
    template_name = 'schedule/course_create.html'
    form_class = CourseCreateForm
    
    def get_success_url(self):
        return reverse('course_add')

    def form_valid(self, form):
        messages.success(
            self.request,
            "Course created successfully!"
        )
        # retrieve the object created before comitting to database
        course = form.save(commit=False)
        # add the domain field
        course.domain = self.student.school
        # save object in db
        course.save()
        return super(CourseCreateView, self).form_valid(form)

course_create = CourseCreateView.as_view()

class CourseAddView(_BaseCourseView):
    template_name = 'schedule/course_add.html'
    form_class = CourseChangeForm

    # get search results (if requested), 
    # and show search box and currently enrolled courses
    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        existing_courses = []
        query = ''
        show_results = False
        if 'q' in request.GET:
            show_results = True
            query = request.GET['q']
            existing_courses = self.search_classes(request)
            logger.debug(existing_courses)

        enrolled_courses = self.request.user.student.courses.all()
        data = {
            'query': query,
            'enrolled_courses': enrolled_courses,
            'course_results': existing_courses,
            'show_results': show_results,
        }

        context_data = Context(self.get_context_data(form=form))
        context_data.update(data)
        return render(request, self.template_name, context_data)

    # using haystack
    def search_classes(self, request):
        form = CourseSearchForm(request.GET)
        courses = form.search().order_by('dept')[:10]

        # student is already enrolled in these classes
        already_enrolled = Course.objects.filter(student=self.student)
        # exclude them from the search results
        for course in already_enrolled:
            courses = courses.exclude(
                content__contains=course.dept,
            )
        # there has to be a better way to do this
        course_list = []
        # annotate the results with number of students in each course
        for course in courses:
            # this is probably 1 db hit per result :\
            c = Course.objects.filter(pk=course.pk).annotate(
                student_count = Count('student')
            )[0]
            course_list.append(c)
        return course_list

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Failed to add course."
        )
        return self.get(self.request)

    def form_valid(self, form):
        # save model manually, don't call save form
        # to not overwrite current classes
        student = self.student
        courses_to_add = form.cleaned_data['courses']
        student.courses.add(courses_to_add[0])

        messages.success(
            self.request,
            "Course added successfully!"
        )
        return super(CourseAddView, self).form_valid(form)

course_add = CourseAddView.as_view()

class CourseRemoveView(_BaseCourseView, AjaxableResponseMixin):
    form_class = CourseChangeForm

    def get(self, request):
        return redirect(reverse('course_add'))

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Failed to delete course"
        )
        if self.request.is_ajax():
            return self.render_to_json_response(dict(form.errors.items()), status=400)
        else:
            return redirect(reverse('course_add'))

    def form_valid(self, form):
        if self.request.is_ajax():
            course = form.cleaned_data['courses']
            for c in course:
                self.student.courses.remove(c)
            messages.success(
                self.request,
                "Course removed successfully"
            )
            data = {
                'messages': self.ajax_messages(),
            }
            return self.render_to_json_response(data)
        else:
            return redirect(reverse('course_add'))

course_remove = CourseRemoveView.as_view()
