# django-wfe

**django-wfe** (Django Workflow Engine) is a Django app that provides multi-step workflow definition and execution tools.

It defines a concept of a Workflow, as a directed graph, which nodes are developer defined Steps (consisting of uniterrupted sequence of logic operations) or Decisions (Steps which support multiple possible transitions, based on a received input from the previous Step). A certain execution of the Workflow is refered to as Job.
Both Steps and Workflows are defined as a python code classes, inheriting from `django_wfe.steps.Step` (optionally, from `django_wfe.steps.Decision`) and `django_wfe.workflow.Workflow` classes accordingly, and are represented in the database for an easy Job serialization, whereas Jobs are classic Django ORM models (`django_wfe.models.Job`) which, among others, keep the serialized state of a certain Workflow execution.


## Requirements
##### Requirements:
* [Django][django] 3.0+
* [PostgreSQL][postgres] 11.7+
* [psycopg2][psycopg2] 2.8+
* [django_dramatiq][django_dramatiq] 0.9+
* [django-rest-framework][djangorestframework] 3.11+ (only needed, if you'll use django-wfe REST API)

##### Implicite requirements (installed along with the django-wfe app):
* [pydantic][pydantic] 1.5+
* [APScheduler][apscheduler] 3.6+

## Example

You can find a reference project implementation for `django-wfe` [here][example].


## Installation

    pip install -e git+https://github.com/geosolutions-it/django-wfe.git#egg=django_wfe

or:

    # NOT YET AVAILABLE
    pip install django-wfe

## Quick Setup

1. In the `settings.py` file:
    * Configure `PostgreSQL` database backend, e.g.:
        
        ``` python
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': os.getenv("DB_NAME", 'postgres'),
                'USER': os.getenv("DB_USER", 'postgres'),
                'PASSWORD': os.getenv("DB_PASSWORD"),
                'HOST': os.getenv("DB_HOST", 'localhost'),
                'PORT': os.getenv("DB_PORT", 5432),
                'CONN_TOUT': 900,
            }
        }
        ```
        For details see: Django [Documentation][django_postgres_integration].
        
    * Configure `django_dramatiq` broker, e.g. for RabbitMQ on localhost's default port:
    
        ``` python
            DRAMATIQ_BROKER = {
                "BROKER": "dramatiq.brokers.rabbitmq.RabbitmqBroker",
                "OPTIONS": {
                    "url": "amqp://localhost:5672",
                },
                "MIDDLEWARE": [
                    "dramatiq.middleware.Prometheus",
                    "dramatiq.middleware.AgeLimit",
                    "dramatiq.middleware.TimeLimit",
                    "dramatiq.middleware.Callbacks",
                    "dramatiq.middleware.Retries",
                    "django_dramatiq.middleware.AdminMiddleware",
                    "django_dramatiq.middleware.DbConnectionsMiddleware",
                ]
            }
            
            DRAMATIQ_TASKS_DATABASE = "default"
        ```
        
        For details see: [django_dramatiq][django_dramatiq] and [dramatiq][dramatiq].

    * Add `django_wfe` to installed apps in , **before** any of your custom applications:
    
        ``` python
        INSTALLED_APPS = [
            # ...
            "django_wfe",
            # "your_app_1",
            # "your_app_2",
            # ...
        ]
        ```
    * Configure path to your `django-wfe` Workflows definition files (Step and Decisions are fetched automatically based on the defined Workflows):
    
        ``` python
        WFE_WORKFLOWS = 'myapp.workflows'
        ```

2. Add django-wfe URL's to the project's `urlpatterns` in `your_project.urls.py` file (remember to install `djangorestframework` frist):

    ``` python   
    urlpatterns = [
        # ...
        path('wfe/', include("django_wfe.urls", namespace="django_wfe")),
    ]
    ```

3. Run migration command to create the django-wfe models:

        python manage.py migrate

## Usage

*Important!* Do **not** use `from something import *` in the files django-wfe is using.

In the current version of the django_wfe it is discouraged to use import all format in all files, especially in Steps, Decisions and Workflows definition files. Usually, the application will not be bothered by such syntax, but the automatical synchronization of the database with your custom WFE models (workflows, steps and decisions) during the runtime may fail.

### Declaring Steps

In a convinient file define your Steps. The Step is a class inheriting from `django_wfe.steps.Step`, which overrides its `execute()` method with a custom logic. `execute()` generally takes only one parameter `_input`, which is a result of the previously executed task. Please note, it is up to you to take care of the `_input` which is received by the Step. The Step executed before the current one in the Workflow does not necessarily need to follow any schema of its output.

The basic Step implementation could look like:

``` python
from django_wfe import steps

class Step1(steps.Step):
    def execute(self, _input=None, *args, **kwargs):
        # some fancy logic here
```

Steps also support exteranal input before conductiong their execution (e.g. User decision, etc.). A need for an external input indicates `UserInputSchema` class defined in the Step definition, which inhterits from `pydantic.BaseModel`, and is used to validate the input before passing it to the Step for execution (for the supported syntax and more details see [pydantic][pydantic]). Such external input is available in the `execute()` method as `exterernal_input` keyword argument.

``` python 
from django_wfe import steps
from pydantic import BaseModel

class Step2(steps.Step):

    class UserInputSchema(BaseModel):
        some_data: int

    def execute(self, _input=None, external_input=None, *args, **kwargs):
        process(external_input['some_data'])
```

### Declaring Decisions

Decisions are an abstract concept of the Step, introduced for an easier management of the project. You can define the decisions in the same file as Steps or separate them, according to your preferences.

Definition of your Decisions should inherit from `django_wfe.steps.Decision` class. Since Decisions are technically speaking Steps, they may also define `execute()` method, but in their case, much more important is `transition()` method, which defines which node should be executed next.
`transition()` method takes the same arguments as Step's `execute()` (including `UserInputSchema` declared external input), but it should return a integer, representing the index of the next Step to execute. For more info please check [Declaring Workflows] chapter.

A minimum implementation of the Decision should look like:

``` python
from django_wfe import steps

class Decision1(steps.Decision):
    def transition(self, _input=None, *args, **kwargs):
        # some fancy logic here, defining int: output
        return output
```

### Declaring Workflows

Workflows (defined in `WFE_WORKFLOWS` file), are classes inheriting form `django_wfe.workflows.Workflow` class, which define DIGRAPH class property. DIGRAPH is a python dict representation of a directed graph. Each key of the DIGRAPH is a graph's node and each value is a list of it's outgoing edges. An order of the edges assigned to the node, corresponds an index returned by the Decision's `transition()` method (in the following example: if the `Decision1.transition()` returns `0`, `Step2a` will be executed as the next one, and in case of `1` it will be `Step2b`).
The beginnning of the workflow should always be marked with `django_wfe.steps.__start__` Step, which supports only one outgoing edge (`transition()` always returns `0`).

``` python
from django_wfe import workflows, steps
from .my_steps import *

class MyWorkflow(workflows.Workflow):
    DIGRAPH = {
        steps.__start__: [Step1],
        Step1: [Decision1],
        Decision1: [Step2a, Step2b],
        Step2a: [Step3],
        Step2b: [Step3],
    }
```

The above defines a simple Workflow representing the following graph:

```
                        Step2a
                    /           \
Step1 -> Decision1                Step3
                    \           /
                        Step2b
```   

### Running Workflows

**Note:** When running the project with django-wfe application, you should run `wfe_watchdog` process, updating the database with the currently used Steps and Decisions, and available Workflows, so the files containing the definitions can be changed during the project runtime. By default, an update is executed every 5 seconds, but it can be customized with `WFE_WATCHDOG_INTERVAL` setting. Providing a non-positive value will result in disabling the updating task. In a separate terminal run:

```
python manage.py wfe_watchdog
```

##### With python functions

There are two functions defined in django-wfe which enable programmic execution and interaction with the Workflows:
* `oder_workflow_execution()` - a function taking Workflow's database ID as an argument, and starting it's execution with the Dramatiq worker as the monitor and executor

    ``` python
    from django_wfe import order_workflow_execution
    
    job_id = order_workflow_execution(workflow_id=1)
    ```

* `provide_external_input()` - In case the Job encounters a Step with an external input required, the Job's execution will be suspended and Job's state will be updated with `django_wfe.models.JobState.INPUT_REQUIRED`. This function, taking Job's database ID and a python dict as arguments, allows to validate the dictionary against the `UserInputSchema` of the currently executed Step, and resume the Job execution. 
    
    ``` python
    from django_wfe import provide_external_input
    from django_wfe.models import Job, JobState
    
    input = {}
    # some fancy logic updating input dict
    
    job = Job.objects.get(id=1)
    if job.state == JobState.INPUT_REUIRED:
        provide_external_input(job_id=job.id, external_data=input)
    ```
    
    **Note:** Currently, there are no hooks whatsoever defined to trigger a callback when a Job encounters a Step requiring an external input.
    
    **Note:** For now, it is your responsibility to provide a logic populating the external input of the Step (whether it's a Django form, an API call, or other).

##### With REST API

If you decided to user django-wfe API, you can simply trigger the Workflow with the REST API, making a POST request to `{url_prefix}/jobs` with the Workflow's ID.
Workflows and Steps can be inspeced with API calls `{url_prefix}/workflows` and `{url_prefix}/steps` accordingly.

**Note:** Currently, providing external input for a Step is not supported with REST API. 

## License

**django-wfe** is licensed under GNU GENERAL PUBLIC LICENSE v3.0.
For details, please check [LICENSE][license].

[example]: https://github.com/geosolutions-it/django-wfe-project
[django]: http://djangoproject.com/
[django_dramatiq]: https://github.com/Bogdanp/django_dramatiq
[dramatiq]: https://dramatiq.io/
[license]: https://github.com/geosolutions-it/django-wfe/blob/master/LICENSE
[pydantic]: https://pypi.org/project/pydantic/
[apscheduler]: https://pypi.org/project/APScheduler/
[djangorestframework]: https://pypi.org/project/djangorestframework/
[postgres]: https://www.postgresql.org/
[django_postgres_integration]: https://docs.djangoproject.com/en/3.0/ref/databases/#postgresql-notes
[psycopg2]: https://pypi.org/project/psycopg2/
