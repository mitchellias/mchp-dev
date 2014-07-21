from allauth.account.decorators import verified_email_required

from django.contrib import messages
from django.conf import settings
from django.core import serializers
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView, DeleteView, UpdateView
from django.views.generic.list import ListView

from haystack.query import SearchQuerySet

from documents.forms import DocumentUploadForm
from documents.models import Document, Upload, DocumentPurchase
from documents.exceptions import DuplicateFileError
from schedule.models import Course

import json
import math
import logging
logger = logging.getLogger(__name__)

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
url: add/
name: document_upload
'''
class DocumentFormView(FormView, AjaxableResponseMixin):
    template_name = 'documents/upload.html'
    form_class = DocumentUploadForm

    def get_success_url(self):
        return reverse('document_list')

    def get(self, request, *args, **kwargs):
        # for search results
        if request.is_ajax():
            return self.autocomplete(request)

        form_class = self.get_form_class()
        form = self.get_form(form_class)
        course_field = form.fields['course']

        enrolled_courses = Course.display_objects.filter(
            student__user = self.request.user
        ).order_by('dept', 'course_number', 'professor')

        course_field.queryset = enrolled_courses
        course_field.empty_label = 'Pick a course'

        # course.display comes from the model
        course_field.label_from_instance = lambda course: course.display()

        data = {
            'enrolled_courses': (enrolled_courses),
        }

        context_data = Context(self.get_context_data(form=form))
        context_data.update(data)
        return render(request, self.template_name, context_data)

    # haystack autocompleter
    def autocomplete(self, request):
        if not 'q' in request.GET:
            return self.render_to_json_response({}, status=400)

        school = self.student.school
        sqs = SearchQuerySet().filter(dept_auto=request.GET['q'])
        suggestions = [result.pk for result in sqs]
        suggestions = list(map(lambda pk: Course.objects.get(pk=pk), suggestions))
        suggestions = filter((lambda course: course.domain == school), suggestions)
        course_data = serializers.serialize('json', suggestions)
        data = json.dumps({
            'results': course_data
        })
        return self.render_to_json_response(data, status=200)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Upload failed."
        )
        return self.get(self.request)

    def form_valid(self, form):
        try:
            doc = form.save()
        except DuplicateFileError as err:
            messages.error(
                self.request,
                err
            )
            return self.get(self.request)

        upload = Upload(document=doc, owner=self.student)
        upload.save()
        messages.success(
            self.request,
            "Upload successful"
        )
        return super(DocumentFormView, self).form_valid(form)

    @method_decorator(verified_email_required)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(DocumentFormView, self).dispatch(*args, **kwargs)

document_upload = DocumentFormView.as_view()

'''
url: /
name: document_list
'''
class DocumentListView(ListView):
    template_name = 'documents/list.html'
    model = Upload

    def get_queryset(self):
        return Upload.objects.all().select_related().order_by('-document__create_date')
        return Upload.objects.filter(owner=self.student).select_related().order_by('-document__create_date')

    def get_context_data(self, **kwargs):
        context = super(DocumentListView, self).get_context_data(**kwargs)
        context['upload_count'] = Upload.objects.filter(owner=self.student).count()
        context['purchase_count'] = DocumentPurchase.objects.filter(student=self.student).count()
        # this kind of defeats the purpose of a list view, but eh
        purchases = DocumentPurchase.objects.filter(student=self.student).select_related().order_by('document__title')
        context['purchases'] = purchases

        return context

    @method_decorator(ensure_csrf_cookie)
    @method_decorator(verified_email_required)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(DocumentListView, self).dispatch(*args, **kwargs)

document_list = DocumentListView.as_view()

'''
url: preview/<uuid>/slug
name: document_preview
'''
class DocumentDetailPreview(DetailView):
    template_name = 'documents/preview.html'
    model = Document

    def post(self, request, *args, **kwargs):
        # for users who are not logged in
        if not self.student:
            return redirect(reverse('landing_page'))

        document = self.get_object()
        # if they already bought the doc
        uploader = Upload.objects.get(document=document).owner
        if DocumentPurchase.objects.filter(document=document, student=self.student).exists() or\
           uploader.pk == self.student.pk:
           # or they uploaded it themselves, redirect to the view of the doc
            return redirect(reverse('document_list') + self.kwargs['uuid'] + '/' + document.slug)

        if not self.student.reduce_points(document.price):
            # student didn't have enough points
            messages.error(
                request,
                "Pump your break kid, you don't have enough points to buy that."
            )
        else:
            # student bought the doc
            purchase = DocumentPurchase(document=document, student=self.student)
            purchase.save()
            # give uploader the points 
            uploader.add_earned_points(math.floor(document.price *
                                                  (settings.MCHP_PRICING['commission_rate'] / 100)))
            uploader.save()

        return redirect(reverse('document_list') + self.kwargs['uuid'] + '/' + document.slug)

    def get(self, request, *args, **kwargs):
        # parent stuff, getting object
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)

        # info about the document
        uploader = Upload.objects.get(document=self.object).owner

        document = self.get_object()
        owns = False
        if not request.user.is_anonymous():
            # check if they already bought the doc
            uploader = Upload.objects.get(document=document).owner
            if DocumentPurchase.objects.filter(document=document, student=self.student).exists() or\
               uploader.pk == self.student.pk:
                owns = True

        # for the form to submit to the right page
        data = {
            'current_path': request.get_full_path(),
            'docs_sold': uploader.sales(),
            'uploader': uploader,
            'student': self.student,
            'reviews': self.object.purchased_document.exclude(review_date=None),
            'review_count': self.object.purchased_document.exclude(review_date=None).count(),
            'uuid': self.kwargs['uuid'],
            'slug': self.object.slug,
            'owns': owns,
        }
        context.update(data)
        return self.render_to_response(context)

    def get_object(self):
        logger.debug(self.kwargs['uuid'])
        return get_object_or_404(self.model, uuid=self.kwargs['uuid'])

    # this page is publically viewable 
    def dispatch(self, *args, **kwargs):
        if self.request.user.is_anonymous():
            self.student = None
        else:
            self.student = self.request.user.student
        return super(DocumentDetailPreview, self).dispatch(*args, **kwargs)

document_preview = DocumentDetailPreview.as_view()

'''
url: <uuid>/slug
name: document_detail
'''
class DocumentDetailView(DetailView):
    template_name = 'documents/view.html'
    model = Document

    def post(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])

    @method_decorator(verified_email_required)
    def get(self, request, *args, **kwargs):
        # parent stuff, getting the object
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)

        # check if user bought the doc
        purchased = DocumentPurchase.objects.filter(document=self.object,
                                                    student=self.student).exists()
        # or if they own the doc
        owner = Upload.objects.get(document=self.object).owner

        # if not, redirect to the preview page
        if not purchased and owner.pk != self.student.pk:
            return redirect(reverse('document_list') + 'preview/' + self.kwargs['uuid'] + '/' +
                            self.object.slug)
        # check if they have reviewed it
        reviewed = False
        if purchased:
            reviewed = DocumentPurchase.objects.filter(document=self.object,
                                                    student=self.student).values_list('review_date',
                                                                                     flat=True)[0]
        # it they uploaded it or already reviewed it, they shouldn't be able to rate it again
        rated = False
        if owner == self.student.pk or reviewed != None:
            rated = True
        context['rated'] = rated
        return self.render_to_response(context)

    def get_object(self):
        return get_object_or_404(self.model, uuid=self.kwargs['uuid'])

    def get_context_data(self, **kwargs):
        context = super(DocumentDetailView, self).get_context_data(**kwargs)
        context['uuid'] = self.kwargs['uuid']
        context['slug'] = self.object.slug
        context['student'] = self.student 
        return context

    # this page needs to be publically viewable to redirect properly
    def dispatch(self, *args, **kwargs):
        if self.request.user.is_anonymous():
            return redirect(reverse('document_list') + 'preview/' + self.kwargs['uuid'])
        else:
            self.student = self.request.user.student
            return super(DocumentDetailView, self).dispatch(*args, **kwargs)

document_detail = DocumentDetailView.as_view()

'''
url: remove/
name: document_delete
'''
class DocumentDeleteView(DeleteView, AjaxableResponseMixin):
    model = Document

    def get_success_url(self):
        return reverse('document_list')

    def get(self, request):
        return redirect(reverse('document_list'))

    def delete(self, request, *args, **kwargs):
        if self.request.is_ajax():
            if 'document' in request.POST:
                data = {}
                doc = Document.objects.filter(
                    pk=request.POST['document'],
                    upload__owner = self.student,
                )
                if not doc:
                    # incorrect pk, or doc belongs to someone else
                    messages.error(
                        self.request,
                        "Document not found."
                    )
                    data['messages'] =  self.ajax_messages()
                    return self.render_to_json_response(data, status=403)
                else:
                    # actually delete document
                    doc[0].delete()
                    messages.success(
                        self.request,
                        "Document deleted successfully."
                    )
            else:
                # no pk sent
                messages.error(
                    self.request,
                    "Document not specified."
                )
            data['messages'] =  self.ajax_messages()
            return self.render_to_json_response(data, status=200)
        else:
            return redirect(reverse('document_list'))


    @method_decorator(verified_email_required)
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(DocumentDeleteView, self).dispatch(*args, **kwargs)

document_delete = DocumentDeleteView.as_view()

'''
url: unpurchase/
name: purchase_delete
'''
class PurchaseDeleteView(DeleteView, AjaxableResponseMixin):
    model = Document

    def get_success_url(self):
        return reverse('document_list')

    def get(self, request):
        return redirect(reverse('document_list'))

    def delete(self, request, *args, **kwargs):
        if self.request.is_ajax():
            if 'document' in request.POST:
                data = {}
                doc = Document.objects.filter(
                    pk=request.POST['document'],
                )
                purchase = DocumentPurchase.objects.filter(document=doc, student=self.student)
                if not purchase.exists():
                    # they didn't buy this doc
                    messages.error(
                        self.request,
                        "Purchased Document not found."
                    )
                    data['messages'] =  self.ajax_messages()
                    return self.render_to_json_response(data, status=403)
                else:
                    # delete purchase record
                    purchase[0].delete()
                    messages.success(
                        self.request,
                        "Document removed successfully."
                    )
            else:
                # no pk sent
                messages.error(
                    self.request,
                    "Document not specified."
                )
            data['messages'] =  self.ajax_messages()
            return self.render_to_json_response(data, status=200)
        else:
            return redirect(reverse('document_list'))

    @method_decorator(verified_email_required)
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(PurchaseDeleteView, self).dispatch(*args, **kwargs)

purchase_delete = PurchaseDeleteView.as_view()

'''
url: review/
name: purchase_update
'''
class PurchaseUpdateView(UpdateView, AjaxableResponseMixin):
    model = DocumentPurchase

    def get_success_url(self):
        return reverse('document_list')

    def get(self, request):
        return redirect(reverse('document_list'))

    def post(self, request, *args, **kwargs):
        if self.request.is_ajax():
            if 'document' in request.POST:
                data = {}
                purchase = DocumentPurchase.objects.get(
                    document__id=request.POST['document'],
                    student = self.student,
                )
                if not purchase:
                    # they didn't buy this doc
                    messages.error(
                        self.request,
                        "You can't review a document you have not purchased."
                    )
                    data['messages'] =  self.ajax_messages()
                    return self.render_to_json_response(data, status=403)
                else:
                    # if review_date exists, document was already reviewed
                    if purchase.review_date:
                        messages.warning(
                            self.request,
                            "You have already reviewed this document."
                        )
                        data['messages'] =  self.ajax_messages()
                        return self.render_to_json_response(data, status=200)

                    # add a review to the purchase record
                    review = request.POST['review'][:250]
                    purchase.review = review

                    # add vote to document record
                    vote = int(request.POST['vote'])
                    if vote == 0:
                        purchase.document.down = purchase.document.down + 1
                    elif vote == 1:
                        purchase.document.up = purchase.document.up + 1
                    else:
                        messages.error(
                            self.request,
                            "Vote not valid"
                        )
                        data['messages'] =  self.ajax_messages()
                        return self.render_to_json_response(data, status=403)
                    messages.success(
                        self.request,
                        "Document reviewed successfully."
                    )
                    # add time stamp
                    purchase.review_date = timezone.now()

                    # save models
                    purchase.save()
                    purchase.document.save()
            else:
                # no pk sent
                messages.error(
                    self.request,
                    "Document not specified."
                )
            data['messages'] =  self.ajax_messages()
            return self.render_to_json_response(data, status=200)
        else:
            return redirect(reverse('document_list'))

    @method_decorator(verified_email_required)
    def dispatch(self, *args, **kwargs):
        self.student = self.request.user.student
        return super(PurchaseUpdateView, self).dispatch(*args, **kwargs)

purchase_update = PurchaseUpdateView.as_view()
