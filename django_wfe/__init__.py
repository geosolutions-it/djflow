"""
A Django app providing multi-step workflow execution tools.
"""

from django.apps import AppConfig
from .app_utils import execute_workflow, provide_input


VERSION = (0, 1, 0)
__version__ = ".".join([str(i) for i in VERSION])
__author__ = "geosolutions-it"
__email__ = "info@geosolutionsgroup.com"
__url__ = "https://github.com/geosolutions-it/django-wfe"
__license__ = "GNU General Public License"


class DjangoWfeConfig(AppConfig):
    name = "django_wfe"
    verbose_name = "Django Workflow Engine"

    def ready(self):
        # register Django system check framework checks
        from . import system_checks


default_app_config = "django_wfe.DjangoWfeConfig"
