from django.core.management import BaseCommand
from django_wfe.utils import set_watchdog_on_wdk_models


class Command(BaseCommand):
    def handle(self, *args, **options):
        set_watchdog_on_wdk_models()
