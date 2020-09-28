"""UI views for the ontologyaccess app"""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

# Projectroles dependency
from projectroles.views import HTTPRefererMixin, LoggedInPermissionMixin

from ontologyaccess.forms import OBOFormatOntologyForm
from ontologyaccess.models import OBOFormatOntology


class OBOFormatOntologyListView(LoggedInPermissionMixin, ListView):
    """OBOFormatOntology list view"""

    model = OBOFormatOntology
    permission_required = 'ontologyaccess.view_list'
    slug_url_kwarg = 'bioontology'
    slug_field = 'sodar_uuid'
    template_name = 'ontologyaccess/list.html'

    def get_queryset(self):
        return OBOFormatOntology.objects.all().order_by('title')


class OBOFormatOntologyDetailView(
    LoggedInPermissionMixin, HTTPRefererMixin, DetailView
):
    """OBOFormatOntology detail view"""

    model = OBOFormatOntology
    permission_required = 'ontologyaccess.update_ontology'
    slug_url_kwarg = 'oboformatontology'
    slug_field = 'sodar_uuid'
    template_name = 'ontologyaccess/obo_detail.html'


class OBOFormatOntologyImportView(
    LoggedInPermissionMixin, HTTPRefererMixin, CreateView
):
    """OBOFormatOntology import/creation view"""

    form_class = OBOFormatOntologyForm
    permission_required = 'ontologyaccess.create_ontology'
    template_name = 'ontologyaccess/obo_import_form.html'

    def form_valid(self, form):
        redirect_url = reverse('ontologyaccess:list')
        self.object = form.save()
        messages.success(
            self.request,
            'OBO Ontology "{}" imported with {} terms.'.format(
                self.object.title, self.object.terms.all().count()
            ),
        )
        return redirect(redirect_url)


class OBOFormatOntologyUpdateView(
    LoggedInPermissionMixin, HTTPRefererMixin, UpdateView
):
    """OBOFormatOntology import/creation view"""

    model = OBOFormatOntology
    form_class = OBOFormatOntologyForm
    permission_required = 'ontologyaccess.create_ontology'
    slug_url_kwarg = 'oboformatontology'
    slug_field = 'sodar_uuid'
    template_name = 'ontologyaccess/obo_import_form.html'

    def form_valid(self, form):
        redirect_url = reverse('ontologyaccess:list')
        self.object = form.save()
        messages.success(
            self.request,
            'OBO Ontology "{}" updated'.format(self.object.title,),
        )
        return redirect(redirect_url)


class OBOFormatOntologyDeleteView(
    LoggedInPermissionMixin, HTTPRefererMixin, DeleteView
):
    """OBOFormatOntology deletion view"""

    model = OBOFormatOntology
    permission_required = 'ontologyaccess.delete_ontology'
    slug_url_kwarg = 'oboformatontology'
    slug_field = 'sodar_uuid'
    template_name = 'ontologyaccess/obo_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, 'Ontology deleted.')
        return reverse('ontologyaccess:list')
