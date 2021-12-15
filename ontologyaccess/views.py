"""UI views for the ontologyaccess app"""

import random

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
from ontologyaccess.models import OBOFormatOntology, OBOFormatOntologyTerm


class OBOFormatOntologyListView(LoggedInPermissionMixin, ListView):
    """OBOFormatOntology list view"""

    model = OBOFormatOntology
    permission_required = 'ontologyaccess.view_list'
    slug_url_kwarg = 'bioontology'
    slug_field = 'sodar_uuid'
    template_name = 'ontologyaccess/list.html'

    def get_queryset(self):
        return OBOFormatOntology.objects.all().order_by('name')


class OBOFormatOntologyDetailView(
    LoggedInPermissionMixin, HTTPRefererMixin, DetailView
):
    """OBOFormatOntology detail view"""

    model = OBOFormatOntology
    permission_required = 'ontologyaccess.update_ontology'
    slug_url_kwarg = 'oboformatontology'
    slug_field = 'sodar_uuid'
    template_name = 'ontologyaccess/obo_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get a random term to test accession URL in the UI
        o = OBOFormatOntology.objects.get(
            sodar_uuid=self.kwargs['oboformatontology']
        )
        terms = OBOFormatOntologyTerm.objects.filter(ontology=o)
        term_count = terms.count()

        if term_count > 0:
            if term_count > 100:
                term_count = 100
            random.seed()
            t = terms[random.randint(0, term_count - 1)]
            context['ex_term'] = t
            context['ex_term_acc'] = o.term_url.format(
                id_space=t.get_id_space(), local_id=t.get_local_id()
            )

        return context


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
                self.object.title, self.object.terms.count()
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
            'OBO Ontology "{}" updated'.format(
                self.object.title,
            ),
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
