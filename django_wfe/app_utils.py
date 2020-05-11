"""
The module implementing functions used among others in the AppConfig, before Django imports work properly.
As long as this module is imported in django_wfe.__init__, all functions should define imports within themselves.
"""
import typing


def execute_workflow(workflow_id: typing.Union[int, str]) -> int:
    """
    A function handling Django WFE Workflow execution order.

    :param workflow_id: django_wfe.models.Workflow record's ID
    :return: Ordered workflow's execution ID (django_wfe.models.Job instance's ID)
    """
    from .models import Workflow, Job
    from .tasks import process_job

    job = Job(workflow=Workflow.objects.get(id=int(workflow_id)))
    job.save()
    process_job.send(job_id=job.id)

    return job.id


def execute_workflow_sync(workflow_id: typing.Union[int, str]):
    """
    A function handling Django WFE Workflow execution synchronously.

    :param workflow_id: django_wfe.models.Workflow record's ID
    :return: Workflow's execution ID (django_wfe.models.Job instance's ID)
    """
    from .models import Workflow, Job
    from .tasks import process_job

    job = Job(workflow=Workflow.objects.get(id=int(workflow_id)))
    job.save()
    process_job(job_id=job.id)

    return job.id


def provide_input(job_id: typing.Union[int, str], external_data: typing.Dict) -> None:
    """
    A function handling Django WFE external input's and resuming the execution of the Workflow.

    :param job_id: django_wfe.models.Job record's ID
    :param external_data: a dictionary containing external data required by the current django_wfe.models.Step
    :return: None
    """
    from .models import Job
    from .tasks import process_job

    job = Job.objects.get(id=job_id)
    job.provide_external_input(external_data)
    process_job.send(job.id)


def set_watchdog_on_wdk_models():
    """
    Method starting a background thread updating database with user defined Steps, Decisions and Workflows.

    :return: None
    """
    import atexit
    from apscheduler.schedulers.background import BackgroundScheduler
    from django.db.utils import ProgrammingError

    from .models import Watchdog
    from .utils import deregister_watchdog, update_wdk_models
    from .settings import WFE_WATCHDOG_INTERVAL

    try:
        watchdog = Watchdog.load()
    except ProgrammingError:
        # raised in case of not existing models in db (e.g. on the python manage.py migrate)
        print("Watchdog singleton cannot be fetched from db.")
        return

    if not watchdog.running and WFE_WATCHDOG_INTERVAL > 0:
        # order deregister_watchdog() executions as exit function.
        atexit.register(deregister_watchdog)

        # mark watchdog as running
        watchdog.running = True
        watchdog.save()
        # schedule periodic watchdog's execution
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(update_wdk_models, "interval", seconds=WFE_WATCHDOG_INTERVAL)
        scheduler.start()
    elif WFE_WATCHDOG_INTERVAL <= 0:
        print(f"Watchdog turned of by WATCHDOG_INTERVAL equal: {WFE_WATCHDOG_INTERVAL}")
