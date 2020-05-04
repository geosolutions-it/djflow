from django.conf import settings

# Python path to the user defined Workflows, e.g.: 'django_wfe_integration.workflows'
WORKFLOWS = getattr(settings, "WFE_WORKFLOWS", None)

# Python path to the user defined Steps, e.g.: 'django_wfe_integration.steps'
STEPS = getattr(settings, "WFE_STEPS", None)

# Python path to the user defined Decisions, by default it's the same as WFE_STEPSz
DECISIONS = getattr(settings, "WFE_DECISIONS", STEPS)
