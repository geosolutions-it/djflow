from django.core.management import BaseCommand

from django_wfe.utils import set_watchdog_on_wdk_models


class Command(BaseCommand):

    help = "Runs Django WFE watchdog process for updating user defined WDK (Workflow Development Kit) models in the database"

    def handle(self, *args, **options):
        set_watchdog_on_wdk_models()
