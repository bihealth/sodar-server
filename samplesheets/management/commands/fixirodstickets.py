"""Management command to find and fix orphaned IrodsAccessTickets objects"""

from datetime import datetime
from typing import Optional

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


class Command(BaseCommand):
    help = (
        'Find iRODS access tickets with no associated IrodsAccessTicket object '
        'in the database, and recreate the missing objects.'
    )

    @classmethod
    def _get_irods_tickets(cls, irods_backend) -> tuple[dict, iRODSPath]:
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
    def _extract_ticket_properties(
        cls, irods_backend, ticket, path
    ) -> Optional[dict]:
        props = {}
        ticket_string = ticket[TicketQuery.Ticket.string]
        ticket_study = irods_backend.get_uuid_from_path(path, 'study')
        if ticket_study:
            try:
                props['study'] = Study.objects.get(sodar_uuid=ticket_study)
            except Study.DoesNotExist:
                logger.warning(
                    f'Ticket {ticket_string} is associated with a Study '
                    f"which doesn't exist ({ticket_study})"
                )
                return None
        else:
            logger.warning(
                f'Ticket {ticket_string} does not have an associated study'
            )
            return None
        ticket_assay = irods_backend.get_uuid_from_path(path, 'assay')
        if ticket_assay:
            try:
                props['assay'] = Assay.objects.get(sodar_uuid=ticket_assay)
            except Assay.DoesNotExist:
                logger.warning(
                    f'Ticket {ticket_string} is associated with an Assay'
                    f"which doesn't exist ({ticket_assay})"
                )
                return None
        props['date_created'] = ticket[TicketQuery.Ticket.create_time]
        ticket_expires = ticket[TicketQuery.Ticket.expiry_ts]
        if ticket_expires:
            props['date_expires'] = datetime.fromtimestamp(int(ticket_expires))
        else:
            props['date_expires'] = None
        return props

    def add_arguments(self, parser):
        parser.add_argument(
            '-c',
            '--check',
            action='store_true',
            help='Check for orphaned tickets, but do not recreate them',
        )

    def handle(self, *args, **options):
        logger.info('Finding orphaned access tickets..')
        orphaned_tickets_count = 0
        irods_backend = plugin_api.get_backend_api('omics_irods')
        default_admin = User.objects.get(
            username=settings.PROJECTROLES_DEFAULT_ADMIN
        )
        check = options.get('check')
        for ticket, path in self._get_irods_tickets(irods_backend):
            ticket_string = ticket[TicketQuery.Ticket.string]
            try:
                IrodsAccessTicket.objects.get(ticket=ticket_string)
                if not check:
                    logger.info(
                        'Found existing object for ticket {ticket_string}'
                    )
            except IrodsAccessTicket.DoesNotExist:
                ticket_props = self._extract_ticket_properties(
                    irods_backend, ticket, path
                )
                if not ticket_props:
                    continue
                obj = IrodsAccessTicket(
                    ticket=ticket_string,
                    path=path,
                    user=default_admin,
                    **ticket_props,
                )
                orphaned_tickets_count += 1
                if not check:
                    obj.save()
                    logger.info(
                        f'Created database object for ticket {ticket_string} '
                        f'in {obj.study.investigation.project.get_log_title()} '
                        f'(UUID={obj.sodar_uuid})'
                    )
        logger.info(
            ('Found' if check else 'Recreated')
            + f' {orphaned_tickets_count} orphaned tickets objects.'
        )
