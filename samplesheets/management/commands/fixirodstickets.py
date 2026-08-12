"""Management command to find and fix orphaned IrodsAccessTickets objects"""

from datetime import datetime
from typing import Optional, Any

from irods.models import TicketQuery
from irods.path import iRODSPath

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.plugins import PluginAPI

from samplesheets.models import Assay, Study, IrodsAccessTicket


logger = ManagementCommandLogger(__name__)
plugin_api = PluginAPI()
User = get_user_model()


# Local constants
ASSAY_DOES_NOT_EXIST = (
    'Ticket {ticket_string} is associated with an Assay '
    "which doesn't exist ({ticket_assay})"
)
STUDY_DOES_NOT_EXIST = (
    'Ticket {ticket_string} is associated with a Study '
    "which doesn't exist ({ticket_study})"
)
STUDY_IS_MISSING = 'Ticket {ticket_string} does not have an associated study'
TICKET_OBJECT_ACTION_COUNT = '{action} {count} orphaned ticket object{plural}'


class Command(BaseCommand):
    help = (
        'Find iRODS access tickets with no associated IrodsAccessTicket object '
        'in the database, and recreate the missing objects.'
    )

    @classmethod
    def _get_irods_tickets(cls, irods_backend: Any) -> tuple[dict, iRODSPath]:
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

    @classmethod
    def _get_ticket_fields(
        cls, irods_backend: Any, ticket: dict, path: iRODSPath
    ) -> Optional[dict]:
        """
        Get the fields needed to construct an IrodsAccessTicket object.

        :param irods_backend: IrodsAPI object
        :param ticket: Ticket dictionary returned by the iRODS API
        :param path: iRODSPath associated to the ticket
        :return: Dictionary of IrodsAccessTicket fields if the ticket is valid,
            "None" if some of the required fields are missing
        """
        fields = {}
        ticket_string = ticket[TicketQuery.Ticket.string]
        ticket_study = irods_backend.get_uuid_from_path(path, 'study')
        if ticket_study:
            try:
                fields['study'] = Study.objects.get(sodar_uuid=ticket_study)
            except Study.DoesNotExist:
                logger.warning(
                    STUDY_DOES_NOT_EXIST.format(
                        ticket_string=ticket_string, ticket_study=ticket_study
                    )
                )
                return None
        else:
            logger.warning(STUDY_IS_MISSING.format(ticket_string=ticket_string))
            return None
        ticket_assay = irods_backend.get_uuid_from_path(path, 'assay')
        if ticket_assay:
            try:
                fields['assay'] = Assay.objects.get(sodar_uuid=ticket_assay)
            except Assay.DoesNotExist:
                logger.warning(
                    ASSAY_DOES_NOT_EXIST.format(
                        ticket_string=ticket_string, ticket_assay=ticket_assay
                    )
                )
                return None
        fields['date_created'] = ticket[TicketQuery.Ticket.create_time]
        ticket_expires = ticket[TicketQuery.Ticket.expiry_ts]
        if ticket_expires:
            fields['date_expires'] = datetime.fromtimestamp(int(ticket_expires))
        else:
            fields['date_expires'] = None
        return fields

    def add_arguments(self, parser):
        parser.add_argument(
            '-c',
            '--check',
            action='store_true',
            help='Check for orphaned tickets, but do not recreate them',
        )

    def handle(self, *args, **options):
        logger.info('Finding orphaned access tickets..')
        orphaned_ticket_count = 0
        irods_backend = plugin_api.get_backend_api('omics_irods')
        default_admin = User.objects.get(
            username=settings.PROJECTROLES_DEFAULT_ADMIN
        )
        check = options.get('check')
        for ticket, path in self._get_irods_tickets(irods_backend):
            ticket_string = ticket[TicketQuery.Ticket.string]
            try:
                IrodsAccessTicket.objects.get(ticket=ticket_string)
            except IrodsAccessTicket.DoesNotExist:
                ticket_fields = self._get_ticket_fields(
                    irods_backend, ticket, path
                )
                if not ticket_fields:
                    continue
                orphaned_ticket_count += 1
                ticket_project = ticket_fields['study'].investigation.project
                if check:
                    logger.info(
                        f'Found orhpaned ticket ({ticket_string}) '
                        f'in {ticket_project.get_log_title()} '
                    )
                else:
                    obj = IrodsAccessTicket(
                        ticket=ticket_string,
                        path=path,
                        user=default_admin,
                        **ticket_fields,
                    )
                    obj.save()
                    logger.info(
                        f'Created database object for ticket {ticket_string} '
                        f'in {ticket_project.get_log_title()} '
                        f'(UUID={obj.sodar_uuid})'
                    )
        logger.info(
            TICKET_OBJECT_ACTION_COUNT.format(
                action='Found' if check else 'Recreated',
                count=orphaned_ticket_count,
                plural='s' if orphaned_ticket_count != 1 else '',
            )
        )
