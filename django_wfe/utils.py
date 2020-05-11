import atexit
import importlib

from django.db.models import ObjectDoesNotExist
from django.db.utils import ProgrammingError
from apscheduler.schedulers.background import BackgroundScheduler

from .settings import WFE_WORKFLOWS
from .models import Step, Workflow, Watchdog
from .workflows import WorkflowType


def set_watchdog_on_wdk_models():
    """
    Method starting a background thread updating database with user defined Steps, Decisions and Workflows.

    :return: None
    """

    try:
        watchdog = Watchdog.load()
    except ProgrammingError:
        # raised in case of not existing models in db (e.g. on the python manage.py migrate)
        print("Watchdog singleton cannot be fetched from db.")
        return

    if not watchdog.running:
        # order deregister_watchdog() executions as exit function.
        atexit.register(deregister_watchdog)

        # mark watchdog as running
        watchdog.running = True
        watchdog.save()
        # schedule periodic watchdog's execution
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(update_wdk_models, "interval", seconds=5)
        scheduler.start()


def deregister_watchdog():
    """
    A function setting Watchdog running flag False.
    Should be executed on the main process exit.

    :return: None
    """
    w = Watchdog.load()
    w.running = False
    w.save()


def update_wdk_models():
    """
    A function iterating over user defined WDK classes (Steps, Decisions, and Workflows),
    updating the database with their representation for the proper Job serialization.

    :return: None
    """

    if WFE_WORKFLOWS is None:
        print(f"WARNING: Module's path for django-wfe Workflows is None.")
        return

    # import the module
    model_definitions_module = importlib.import_module(WFE_WORKFLOWS)
    # refresh the module to attach all the newest changes
    importlib.reload(model_definitions_module)

    models = [
        (name, cls)
        for name, cls in model_definitions_module.__dict__.items()
        if isinstance(cls, WorkflowType)
    ]

    for name, cls in models:
        model_path = f"{WFE_WORKFLOWS}.{name}"

        steps_cls = cls._get_steps_classes()

        # update Workflow model entries
        try:
            Workflow.objects.get(path=model_path)
        except ObjectDoesNotExist:
            try:
                Workflow(name=name, path=model_path).save()
            except Exception as e:
                print(
                    f"SKIPPING Automatic mapping {model_path}: failed due to the exception:\n{type(e).__name__}: {e}"
                )

        # update Step model instances defined by the Workflow
        for step in steps_cls:
            step_path = f"{step.__module__}.{step.__name__}"
            try:
                Step.objects.get(path=step_path)
            except ObjectDoesNotExist:
                try:
                    Step(name=step.__name__, path=step_path).save()
                except Exception as e:
                    print(
                        f"SKIPPING Automatic mapping {step_path}: failed due to the exception:\n{type(e).__name__}: {e}"
                    )
