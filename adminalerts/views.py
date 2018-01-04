from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import DetailView, UpdateView, CreateView, \
    DeleteView, ListView
from django.views.generic.edit import ModelFormMixin

# Projectroles dependency
# TBD: Ok to depend on Projectroles here even though this is not a project app?
from projectroles.views import LoggedInPermissionMixin

from .forms import AdminAlertForm
from .models import AdminAlert


# Listing/details views --------------------------------------------------------


class AdminAlertListView(LoggedInPermissionMixin, ListView):
    """Alert list view"""
    permission_required = 'adminalerts.view_alerts'
    template_name = 'adminalerts/alert_list.html'
    model = AdminAlert
    paginate_by = settings.ADMINALERTS_PAGINATION

    def get_queryset(self):
        return AdminAlert.objects.all().order_by('-pk')


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
