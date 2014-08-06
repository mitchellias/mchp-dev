from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.views.generic.edit import FormView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.template import Context
from django.db.models import Count
from django.db import IntegrityError
from django.http import HttpResponse
from django.core import serializers

from lib.decorators import school_required
from documents.models import Document
from schedule.forms import CourseCreateForm, CourseChangeForm, CourseSearchForm
from schedule.models import Course, School, SchoolQuicklink
from user_profile.models import Enrollment

from haystack.query import SQ

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
    @method_decorator(school_required)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(_BaseCourseView, self).dispatch(*args, **kwargs)

class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)

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
        # retrieve the object created before comitting to database
        course = form.save(commit=False)
        # add the domain field
        course.domain = self.student.school
        # try to save course in db
        try:
            course.save()
        except IntegrityError:
            messages.error(
                self.request,
                "This course already exists."
            )
            return super(CourseCreateView, self).form_invalid(form)
        # add student to course
        student = self.student
        enroll = Enrollment(student=student, course=course)
        enroll.save()

        messages.success(
            self.request,
            "Course created successfully!"
        )
        return super(CourseCreateView, self).form_valid(form)

course_create = CourseCreateView.as_view()

class CourseAddView(_BaseCourseView, AjaxableResponseMixin):
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
        enrolled_courses = Course.objects.filter(student=self.student).order_by(
            'dept', 'course_number', 'professor'
        )
        # user performed a search
        if 'q' in request.GET:
            show_results = True
            query = request.GET['q']
            if query != '':
                existing_courses = self.search_classes(request, enrolled_courses)

        data = {
            'query': query,
            'enrolled_courses': enrolled_courses,
            'course_results': existing_courses,
            'show_results': show_results,
        }

        context_data = Context(self.get_context_data(form=form))
        # context acts like a stack here, update is a push to combine 
        context_data.update(data)
        return render(request, self.template_name, context_data)

    # using haystack
    def search_classes(self, request, already_enrolled):
        # haystack stuff
        form = CourseSearchForm(request.GET)
        sq = SQ()

        # add a filter for already enrolled classes
        for course in already_enrolled:
            sq.add(~SQ(
                dept=course.dept, 
                course_number=course.course_number,
                professor=course.professor,
            ), SQ.OR)

        # perform search 
        if not already_enrolled:
            courses = form.search().filter()
        else:
            courses = form.search().filter(sq)

        # annotate the results with number of students in each course
        # first get all primary keys from the search results
        pks = list(map((lambda c: c.pk), courses))
        course_list = Course.objects.filter(
            pk__in=pks, 
            # filter out other schools
            domain=self.student.school
        )\
        .order_by('dept', 'course_number', 'professor')\
        .annotate(student_count = Count('student'))

        return course_list

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Failed to add course."
        )
        if self.request.is_ajax():
            return self.render_to_json_response(dict(form.errors.items()), status=400)
        else:
            return self.get(self.request)

    def form_valid(self, form):
        # save model manually, don't call save form
        # form.save() would overwrite current classes instead of appending
        student = self.student
        course_to_add = form.cleaned_data['courses'][0]
        enroll = Enrollment(student=student, course=course_to_add)
        enroll.save()

        messages.success(
            self.request,
            "Course added successfully!"
        )

        if self.request.is_ajax():
            course = serializers.serialize('json', [course_to_add])
            data = {
                'messages': self.ajax_messages(),
                'course': course,
            }
            return self.render_to_json_response(data)
        else:
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
                enroll = Enrollment.objects.filter(
                    student=self.student,
                    course=c,
                )
                enroll.delete()
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

'''
url: /school/course/<number>/<slug>/
url: /school/course/<number>/
name: course
'''
class CourseView(DetailView):
    template_name = 'schedule/course.html'
    model = Course

    def get_object(self):
        return get_object_or_404(self.model, id=self.kwargs['number'])

    def get(self, request, *args, **kwargs):
        # if the user types a different slug, and that slug is actually a course that exists
        # redirect to that course instead, otherwise just use the pk value and ignore the slug
        if 'slug' in kwargs and not request.user.is_anonymous():
            slug = self.kwargs['slug']
            number = self.kwargs['number']
            course = Course.objects.filter(name=slug.upper(),
                                           domain=self.request.user.student.school)
            if course.exists() and course[0].pk != int(number):
                kw = {
                    'number': course[0].pk,
                    'slug': slug,
                }
                return redirect(reverse('course_slug', kwargs=kw))
        return super(CourseView, self).get(self, request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CourseView, self).get_context_data(**kwargs)
        docs = self.object.document_set.all(
        ).annotate(
            sold=Count('purchased_document__document'),
        ).extra(select = {
            'review_count': 'SELECT COUNT(*) FROM "documents_documentpurchase"'+ \
            'WHERE ("documents_documentpurchase"."document_id" = "documents_document"."id"' +\
            'AND NOT ("documents_documentpurchase"."review_date" IS NULL))'
        }).order_by('-sold')[:15]

        context['popular_documents'] = docs
        if self.student:
            context['student'] = self.student
            context['enrolled'] = Course.objects.filter(pk=self.object.pk,
                                                        student=self.student
                                                       ).exists()
        return context

    def dispatch(self, *args, **kwargs):
        if self.request.user.student_exists():
            self.student = self.request.user.student
        else:
            self.student = None
        return super(CourseView, self).dispatch(*args, **kwargs)

course = CourseView.as_view()

'''
url: /school/course/
name: course_list
'''
class CourseListView(ListView):
    template_name = 'schedule/course_list.html'

    def get(self, request, *args, **kwargs):
        if not 'school' in request.GET:
            return super(CourseListView, self).get(self, request, *args, **kwargs)
        else:
            data = {
                'course_list': Course.objects.filter(
                    domain__name__icontains=request.GET['school'].lower()
                ).order_by('dept', 'course_number', 'professor',)
            }
            return render(request, self.template_name, data)

    def get_queryset(self):
        if self.student:
            return Course.objects.filter(
                domain=self.request.user.student.school
            ).order_by('dept', 'course_number', 'professor',)
        else:
            return []

    @method_decorator(school_required)
    def dispatch(self, *args, **kwargs):
        if self.request.user.student_exists():
            self.student = self.request.user.student
        return super(CourseListView, self).dispatch(*args, **kwargs)

course_list = CourseListView.as_view()

'''
url: /school/<number>/name
name: school
'''
class SchoolView(DetailView):
    template_name = 'schedule/school.html'
    model = School

    def get_object(self):
        return get_object_or_404(self.model, id=self.kwargs['number'])

    def get_context_data(self, **kwargs):
        context = super(SchoolView, self).get_context_data(**kwargs)
        docs = ['what', 'um']
        docs = Document.objects.filter(
            course__in = self.object.course_set.all()
        ).annotate(
            sold=Count('purchased_document__document')
        ).extra(select = {
            'review_count': 'SELECT COUNT(*) FROM "documents_documentpurchase"'+ \
            'WHERE ("documents_documentpurchase"."document_id" = "documents_document"."id"' +\
            'AND NOT ("documents_documentpurchase"."review_date" IS NULL))'
        }).order_by('-sold')[:15]

        context['popular_documents'] = docs
        links = SchoolQuicklink.objects.filter(
            domain=self.get_object
        ).order_by('quick_link')
        context['links'] = links
        return context

school = SchoolView.as_view()

'''
url: /school/
name: school_list
'''
class SchoolListView(ListView):
    template_name = 'schedule/school_list.html'
    model = School

    def get_queryset(self):
        return School.objects.all().order_by('name')

school_list = SchoolListView.as_view()

'''
url: /classes/
name: classes
'''
class ClassesView(View):
    template_name = 'schedule/classes.html'

    def random_mix(self, seq_a, seq_b):
        import random
        iters = [iter(seq_a), iter(seq_b)]
        lens = [len(seq_a), len(seq_b)]
        while all(lens):
            r = random.randrange(sum(lens))
            itindex = r < lens[0]
            it = iters[itindex]
            lens[itindex] -= 1
            yield next(it)
        for it in iters:
            for x in it: yield x
            iters = [iter(seq_a), iter(seq_b)]

    def get(self, request, *args, **kwargs):
        data = {}
        courses = Course.objects.filter(student__user=self.request.user).annotate(
            doc_count=Count('document')
        )
        for course in courses:
            docs = Document.objects.filter(course=course).annotate(
                sold=Count('purchased_document__document'),
            ).extra(select = {
                'review_count': 'SELECT COUNT(*) FROM "documents_documentpurchase"'+ \
                'WHERE ("documents_documentpurchase"."document_id" = "documents_document"."id"' +\
                'AND NOT ("documents_documentpurchase"."review_date" IS NULL))',
            }).select_related('course').order_by('-sold')[:15]

            setattr(course, 'documents', docs)

            act = Document.objects.recent_events(course)

            # get some of the latest people to join your classes
            latest_joins = list(Enrollment.objects.filter(
                course=course
            ).order_by('join_date')[:5])
            from collections import namedtuple
            Activity = namedtuple('Activity', ['type', 'title', 'time', 'user'])

            # make the list unique
            latest_joins = list(set(latest_joins))

            joins = []
            for join in latest_joins:
                joins.append(Activity('join', join.student.name, join.join_date, ''))

            both = list(self.random_mix(act, joins))
            setattr(course, 'activity', both)

        data['course_list'] = courses

        return render(request, self.template_name, data)

    @method_decorator(school_required)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(ClassesView, self).dispatch(*args, **kwargs)

classes = ClassesView.as_view()
