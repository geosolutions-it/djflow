import os
from django.conf import settings

# Python path to the user defined Workflows, e.g.: 'django_wfe_integration.workflows'
WFE_WORKFLOWS = getattr(settings, "WFE_WORKFLOWS", None)


# Interval between updates of the WDK models in seconds
WFE_WATCHDOG_INTERVAL = getattr(settings, "WFE_WATCHDOG_INTERVAL", 5)


# Path to the Job logs directory
default_log_path = (
    os.path.join(settings.BASE_DIR, "logs_wfe")
    if getattr(settings, "BASE_DIR", None) is not None
    else None
)
WFE_LOG_DIR = getattr(settings, "WFE_LOG_DIR", default_log_path)
