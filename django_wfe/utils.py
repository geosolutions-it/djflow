import importlib

from .settings import STEPS, DECISIONS, WORKFLOWS
from .steps import StepType
from .workflows import WorkflowType
from .models import Step, Workflow, Watchdog


class JobState:
    PENDING = "PENDING"
    ONGOING = "ONGOING"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    INPUT_RECEIVED = "INPUT_RECEIVED"
    FAILED = "FAILED"
    FINISHED = "FINISHED"


def update_wdk_models():
    """
    A function iterating over user defined WDK classes (Steps, Decisions, and Workflows),
    updating the database with their representation for the proper Job serialization.

    :return: None
    """

    # update Steps with the starting step
    if not Step.objects.filter(path=f"{__package__}.steps.__start__"):
        Step(name="__start__", path=f"{__package__}.steps.__start__").save()

    # update user created steps
    update_wdk_model(STEPS, Step, StepType)
    # update user created decisions, if not present in steps module
    if STEPS != DECISIONS:
        update_wdk_model(DECISIONS, Step, StepType)
    # update user created workflows
    update_wdk_model(WORKFLOWS, Workflow, WorkflowType)


def update_wdk_model(module_path: str, model: type, model_type: type) -> None:
    """
    A function updating the database with a certain user defined WDK class

    :param module_path: python path (dot notation) to the WKD classes definition module
    :param model: database model of WDK class representation
    :param model_type: WDK class's type (metaclass)
    :return: None
    """
    from django.db.models import ObjectDoesNotExist

    if module_path is None:
        print(f"WARNING: Module's path for model {model} is None.")
        return

    # import the module
    model_definitions_module = importlib.import_module(module_path)
    # refresh the module to attach all the newest changes
    importlib.reload(model_definitions_module)

    models = [
        name
        for name, cls in model_definitions_module.__dict__.items()
        if isinstance(cls, model_type)
    ]

    for name in models:
        model_path = f"{module_path}.{name}"

        try:
            model.objects.get(path=model_path)
        except ObjectDoesNotExist:
            try:
                model(name=name, path=model_path).save()
            except Exception as e:
                print(
                    f"SKIPPING Automatic mapping {module_path}: failed due to the exception:\n{type(e).__name__}: {e}"
                )


def deregister_watchdog():
    """
    A function setting Watchdog running flag False.
    Should be executed on the main process exit.

    :return: None
    """

    w = Watchdog.load()
    w.running = False
    w.save()
