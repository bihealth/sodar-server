"""Management command to find and fix orphaned IrodsAccessTickets objects"""

from datetime import datetime

from irods.models import TicketQuery
from irods.path import iRODSPath

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.plugins import PluginAPI

from irodsbackend.api import IrodsAPI

from samplesheets.models import Assay, Study, IrodsAccessTicket


logger = ManagementCommandLogger(__name__)
plugin_api = PluginAPI()
User = get_user_model()


class Command(BaseCommand):
    help = (
        'Find iRODS access tickets with no associated IrodsAccessTicket object '
        'in the database, and recreate the missing objects.'
    )

    @classmethod
    def _find_irods_tickets(cls, irods_backend: IrodsAPI) -> tuple[str, str]:
        """
        Iterator for iRODS tickets.

        :param irods_backend: IrodsAPI object
        :return: Tuples of ticket query results and their associated path
        """
        with irods_backend.get_session() as irods:
            coll_tickets = irods.query(
                TicketQuery.Ticket, TicketQuery.Collection
            )
            data_tickets = irods.query(
                TicketQuery.Ticket, TicketQuery.DataObject
            )
            for ticket in coll_tickets.get_results():
                yield (ticket, iRODSPath(ticket[TicketQuery.Collection.name]))
            for ticket in data_tickets.get_results():
                yield (
                    ticket,
                    iRODSPath(
                        ticket[TicketQuery.DataObject.coll],
                        ticket[TicketQuery.DataObject.name],
                    ),
                )

    def add_arguments(self, parser):
        parser.add_argument(
            '-c',
            '--check',
            action='store_true',
            help='Check for orphaned tickets, but do not recreate them',
        )

    def handle(self, *args, **options):
        irods_backend = plugin_api.get_backend_api('omics_irods')
        default_admin = User.objects.get(
            username=settings.PROJECTROLES_DEFAULT_ADMIN
        )
        check = options.get('check')
        for ticket, path in self._find_irods_tickets(irods_backend):
            ticket_string = ticket[TicketQuery.Ticket.string]
            try:
                IrodsAccessTicket.objects.get(ticket=ticket_string)
                logger.info(f'Found existing ticket object for {ticket_string}')
            except IrodsAccessTicket.DoesNotExist:
                ticket_study = irods_backend.get_uuid_from_path(path, 'study')
                if ticket_study:
                    ticket_study = Study.objects.get(sodar_uuid=ticket_study)
                else:
                    logger.warning(
                        f'Ticket {ticket_string} does not have '
                        'an associated study'
                    )
                    continue
                ticket_assay = irods_backend.get_uuid_from_path(path, 'assay')
                if ticket_assay:
                    ticket_assay = Assay.objects.get(sodar_uuid=ticket_assay)
                ticket_expires = ticket[TicketQuery.Ticket.expiry_ts]
                if ticket_expires:
                    ticket_expires = datetime.fromtimestamp(int(ticket_expires))
                obj = IrodsAccessTicket(
                    study=ticket_study,
                    assay=ticket_assay,
                    ticket=ticket_string,
                    path=path,
                    user=default_admin,
                    date_created=ticket[TicketQuery.Ticket.create_time],
                    date_expires=ticket_expires,
                )
                logger.info(
                    f'Need to recreate ticket object for {ticket_string} (\n'
                    f'\tstudy: {obj.study.sodar_uuid} ({obj.study}),\n'
                    f'\tassay: {obj.assay.sodar_uuid if obj.assay else None},\n'
                    f'\tticket: {obj.ticket},\n'
                    f'\tpath: {obj.path},\n'
                    f'\tuser: {obj.user},\n'
                    f'\tdate_created: {obj.date_created},\n'
                    f'\tdate_expires: {obj.date_expires},\n'
                    ')'
                )
                if not check:
                    obj.save()
