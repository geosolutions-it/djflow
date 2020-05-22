import atexit
import importlib
from collections.abc import Iterable

from django.db.models import ObjectDoesNotExist
from django.db.utils import ProgrammingError
from apscheduler.schedulers.background import BlockingScheduler

from .settings import WFE_WORKFLOWS, WFE_WATCHDOG_INTERVAL
from .models import Job, Workflow, Watchdog
from .workflows import WorkflowType


def set_watchdog_on_wdk_models():
    """
    Method updating database with user defined Workflows.

    :return: None
    """

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
        scheduler = BlockingScheduler(daemon=True)
        scheduler.add_job(update_wdk_models, "interval", seconds=WFE_WATCHDOG_INTERVAL)
        scheduler.start()
    elif WFE_WATCHDOG_INTERVAL <= 0:
        print(
            f"Watchdog turned of by WFE_WATCHDOG_INTERVAL equal: {WFE_WATCHDOG_INTERVAL}"
        )
    elif watchdog.running:
        print(f"Watchdog process already running.")


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
    A function iterating over user defined WDK classes (Workflows),
    updating the database with their representation for the proper Job serialization.

    :return: None
    """

    if WFE_WORKFLOWS is None:
        print(f"WARNING: Module's path for django-wfe Workflows is None.")
        return

    if not isinstance(WFE_WORKFLOWS, str) and isinstance(WFE_WORKFLOWS, Iterable):
        wfe_workflow_files = WFE_WORKFLOWS
    else:
        wfe_workflow_files = [WFE_WORKFLOWS]

    # insert missing workflows to the database
    for wfe_workflow_file in wfe_workflow_files:

        # import the module
        model_definitions_module = importlib.import_module(wfe_workflow_file)
        # refresh the module to attach all the newest changes
        importlib.reload(model_definitions_module)

        models = [
            (name, cls)
            for name, cls in model_definitions_module.__dict__.items()
            if isinstance(cls, WorkflowType)
        ]

        for name, cls in models:
            model_path = f"{wfe_workflow_file}.{name}"

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

    # remove deleted workflows from the database
    for workflow in Workflow.objects.all():
        try:
            # dynamic import of the Workflow class
            module_path, class_ = workflow.path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            importlib.reload(module)

            WorkflowClass = getattr(module, class_)
        except Exception:
            workflow.deleted = True
            workflow.save()
        else:
            if workflow.deleted:
                workflow.deleted = False
                workflow.save()
