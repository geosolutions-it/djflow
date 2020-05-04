======================
Django Workflow Engine
======================

Django WFE is a Django app to conduct multi-step workflows.

Detailed documentation is in the "docs" directory.

Quick start
-----------

1. Add "polls" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'django_wfe',
    ]

2. Include the polls URLconf in your project urls.py like this::

    path('wfe/', include('django_wfe.urls')),

3. Run ``python manage.py migrate`` to create the django-wfe models.
