from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, DetailView, UpdateView,\
    CreateView, DeleteView, View
from django.views.generic.edit import ModelFormMixin

from rules.contrib.views import PermissionRequiredMixin, redirect_to_login

# Projectroles dependency
# TBD: Ok to depend on Projectroles here even though this is not a project app?
from projectroles.views import LoggedInPermissionMixin

from .forms import AdminAlertForm
from .models import AdminAlert


# Listing/details views --------------------------------------------------------


class AdminAlertListView(LoggedInPermissionMixin, TemplateView):
    """Alert list view"""
    permission_required = 'adminalerts.view_alerts'
    template_name = 'adminalerts/alert_list.html'

    def get_context_data(self, *args, **kwargs):
        """Override get_context_data() for list content"""
        context = super(AdminAlertListView, self).get_context_data()
        context['alerts'] = AdminAlert.objects.all().order_by('-pk')
        return context


class AdminAlertDetailView(LoggedInPermissionMixin, DetailView):
    """Alert detail view"""
    permission_required = 'adminalerts.view_alerts'
    template_name = 'adminalerts/alert_detail.html'
    model = AdminAlert


# Modification views -----------------------------------------------------------


class AdminAlertModifyMixin(ModelFormMixin):
    def form_valid(self, form):
        form.save()
        form_action = 'update' if self.object else 'create'
        messages.success(self.request, 'Alert {}d.'.format(form_action))
        return HttpResponseRedirect(reverse('alert_list'))


class AdminAlertCreateView(
        LoggedInPermissionMixin, AdminAlertModifyMixin, CreateView):
    """AdminAlert creation view"""
    model = AdminAlert
    form_class = AdminAlertForm
    permission_required = 'adminalerts.create_alert'

    def get_form_kwargs(self):
        """Override passing arguments to form"""
        kwargs = super(AdminAlertCreateView, self).get_form_kwargs()
        kwargs.update(self.kwargs)
        kwargs.update({'current_user': self.request.user})
        return kwargs


class AdminAlertUpdateView(
        LoggedInPermissionMixin, AdminAlertModifyMixin, UpdateView):
    """AdminAlert updating view"""
    model = AdminAlert
    form_class = AdminAlertForm
    permission_required = 'adminalerts.update_alert'


class AdminAlertDeleteView(
        LoggedInPermissionMixin, DeleteView):
    """AdminAlert deletion view"""
    model = AdminAlert
    permission_required = 'adminalerts.update_alert'

    def get_success_url(self):
        """Override for redirecting alert list view with message"""
        messages.success(self.request, 'Alert deleted.')
        return reverse('alert_list')
