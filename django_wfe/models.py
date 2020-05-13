import os
import uuid
import typing
import datetime
import importlib
import traceback

from django.db import models
from django.contrib.postgres.fields import JSONField

from .logging import Tee
from .settings import WFE_LOG_DIR
from .exceptions import FinishedWorkflow, InputRequired, WrongState


class JobState:
    PENDING = "PENDING"
    ONGOING = "ONGOING"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    INPUT_RECEIVED = "INPUT_RECEIVED"
    FAILED = "FAILED"
    FINISHED = "FINISHED"


def default_storage():
    return {"data": []}


class Singleton(models.Model):
    """
    Abstract class for Django Singleton models

    Usage:
    singleton = Singleton.load()

    Warning: "delete selected objects" action in the Admin panel uses QuerysSet.delete() instead of
    Model.delete(). To prevent unexpected behavior, remember to restrict deletion permissions in
    the model's admin.ModelAdmin class accordingly.
    """

    class Meta:
        abstract = True

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass


class Step(models.Model):
    """
    A database representation of the Django WFE's Setps and Decisions implementations.
    """

    name = models.CharField(max_length=250)
    path = models.CharField(
        max_length=250, help_text="Python path of the Step definition", unique=True
    )

    def __str__(self):
        return self.path


class Workflow(models.Model):
    """
    A database representation of the Django WFE's Workflows implementations.
    """

    name = models.CharField(max_length=250)
    path = models.CharField(
        max_length=250, help_text="Python path of the Workflow definition", unique=True
    )

    def __str__(self):
        return self.path


class Job(models.Model):
    """
    A table keeping the serialized state of a certain workflows' executions.
    """

    uuid = models.UUIDField(default=uuid.uuid4)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    current_step = models.ForeignKey(
        Step, on_delete=models.CASCADE, null=True, default=None
    )
    current_step_number = models.IntegerField(default=0)
    storage = JSONField(
        help_text="Serialized output of executed Workflow's Steps and data shared between Steps",
        default=default_storage,
    )
    state = models.CharField(max_length=20, null=True, default=JobState.PENDING)
    logfile = models.CharField(max_length=300, default=None)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # assign default Job starting step as current
        if self.current_step is None:
            try:
                self.current_step = Step.objects.get(name="__start__")
            except models.ObjectDoesNotExist:
                print(
                    "Step '__start__' not found. Please make sure it is present in the database before ordering a Job."
                )

        if self.logfile is None:
            self.logfile = os.path.join(
                WFE_LOG_DIR, f"{self.workflow.name}_{self.uuid}.log"
            )

        super().save()

    def __str__(self):
        return f"{self.workflow.name}:{self.id}"

    @staticmethod
    def import_class(path: str):
        """
        Method importing a certain class from python module.

        :param path: python path (dot notation) to the class
        :return: class object under located under the provided path
        """
        module, class_ = path.rsplit(".", 1)
        Class = getattr(importlib.import_module(module), class_)

        return Class

    def execute(self):
        """
        A method executing the Workflow until the end or until a Step with required user input is encountered

        :return: None
        """
        try:
            self._run_next()
        except Exception:
            self._log("---- WORKFLOW EXECUTION FAILED ----")
            self.state = JobState.FAILED
            self.save()

    def provide_external_input(self, external_data: typing.Dict):
        """
        A method gathering user's input for the current Step

        :return:
        :raises: pydantic.ValidationError
        """
        CurrentStep = self.import_class(self.current_step.path)

        if not CurrentStep.UserInputSchema.__fields__:
            raise WrongState(
                f"Current Workflow's Step {CurrentStep} does not accept external input."
            )

        if self.state != JobState.INPUT_REQUIRED:
            raise WrongState(f"Wrong Workflow's state: {self.state}.")

        # pydantic validate the data structure
        external_data = CurrentStep.UserInputSchema(**external_data)

        # update serialized job's state with provided external data
        try:
            self.storage["data"][self.current_step_number][
                "external_data"
            ] = external_data.dict()
        except IndexError:
            self.storage["data"].append(
                {"step": self.current_step.path, "external_data": external_data.dict()}
            )

        self.state = JobState.INPUT_RECEIVED
        self.save()

    def _run_next(self):
        """
        A method recursively executing Steps of the Workflow

        :return: None
        """
        StepClass = self.import_class(self.current_step.path)
        WorkflowClass = self.import_class(self.workflow.path)

        try:
            current_step = self._step_initialize(StepClass)
        except InputRequired:
            return

        # previous step result
        _input = (
            self.storage["data"][self.current_step_number - 1]["result"]
            if self.storage["data"]
            else None
        )

        result = self._step_execute(current_step, _input=_input)
        transition = self._step_calculate_transition(
            current_step, result=result, _input=_input
        )

        try:
            self._workflow_transition(WorkflowClass, StepClass, transition)
        except FinishedWorkflow:
            return

        self._run_next()

    def _step_initialize(self, StepClass: type):
        """
        Method initializing currently executed Step instance

        :param StepClass: class object inheriting from django_wfe.steps.Step
        :raises InputRequired: in case current Step requires an external input (similarly to StopIteration exception)
        :return: StepClass instance
        """
        step = StepClass(job=self)

        # break execution if input is required by the current Step
        if step.requires_input and self.state != JobState.INPUT_RECEIVED:
            self.state = JobState.INPUT_REQUIRED
            self.save()

            self._log(
                f"Step #{self.current_step_number} '{StepClass.__name__}': input required"
            )

            raise InputRequired
        else:
            self._log(
                f"Step #{self.current_step_number} '{step.__class__.__name__}': processing started"
            )

        self.state = JobState.ONGOING
        self.save()

        return step

    def _step_execute(self, step, _input=None):
        """
        Method conducting execute() method of the Step

        :param step: instance of the class inheriting from django_wfe.steps.Step
        :param _input: previous step's output
        :return: result of the step execution
        """

        self._log(
            f"Step #{self.current_step_number} '{step.__class__.__name__}': performing execute():"
        )

        try:
            with Tee(self.logfile, "a"):
                result = step._perform_execute(_input=_input, logfile=self.logfile)

        except Exception as exception:
            # log exception in the logfile
            with open(self.logfile, "a") as log:
                log.write(
                    "".join(
                        traceback.TracebackException.from_exception(exception).format()
                    )
                )
            raise

        self._log(
            f"Step #{self.current_step_number} '{step.__class__.__name__}': execution finished successfully with a result: {result}"
        )

        try:
            self.storage["data"][self.current_step_number]["result"] = result
        except IndexError:
            self.storage["data"].append(
                {"step": self.current_step.path, "result": result}
            )
        self.save()

        return result

    def _step_calculate_transition(self, step, _input=None, result=None) -> int:
        """
        Method conducting transition() method of the Step

        :param step: instance of the class inheriting from django_wfe.steps.Step
        :param _input: previous step's output
        :param result: result of the step execution
        :return: index of the next step in the Workflow's DIGRAPH
        """
        self._log(
            f"Step #{self.current_step_number} '{step.__class__.__name__}': performing transition():"
        )

        try:
            with Tee(self.logfile, "a"):
                transition = step._perform_transition(_input=_input, result=result)

        except Exception as exception:
            # log exception in the logfile
            with open(self.logfile, "a") as log:
                log.write(
                    "".join(
                        traceback.TracebackException.from_exception(exception).format()
                    )
                )
            raise

        self._log(
            f"Step #{self.current_step_number} '{step.__class__.__name__}': transition finished successfully with a result: {transition}"
        )

        return transition

    def _workflow_transition(
        self, WorkflowClass: type, StepClass: type, transition: int = 0
    ):
        """
        Method moving Job's execution to the next node of DIGRAPH

        :param WorkflowClass: class object inheriting from django_wfe.workflows.Workflow
        :param StepClass: class object inheriting from django_wfe.steps.Step
        :param transition: index of the next Step in the Workflow's DIGRAPH
        :raises FinishedWorkflow: in case currently executed Step is the last one in the workflow (similarly to StopIteration exception)
        :return: None
        """

        if (
            WorkflowClass.DIGRAPH.get(StepClass) is None
            or len(WorkflowClass.DIGRAPH.get(StepClass)) == 0
        ):
            # workflow's finished
            self.state = JobState.FINISHED
            self.save()

            self._log(f"---- WORKFLOW FINISHED SUCCESSFULLY ----")

            raise FinishedWorkflow

        self._log(
            f"Step #{self.current_step_number} '{StepClass.__name__}': step finished"
        )

        self.current_step = Step.objects.get(
            path=(
                WorkflowClass.DIGRAPH.get(StepClass)[transition].__module__
                + "."
                + WorkflowClass.DIGRAPH.get(StepClass)[transition].__name__
            )
        )
        self.current_step_number += 1
        self.save()

    def _log(self, msg: str):
        """
        Method logging the message to file and printing it to stdout

        :param msg: string to be logged to file and printed on stdout
        :return: None
        """

        with Tee(self.logfile, "a"):
            print(f"{datetime.datetime.now()} {msg}")


class Watchdog(Singleton):
    """
    A flag model for the watchdog thread (updating database with user defined WDK models)
    to be triggered only once
    """

    running = models.BooleanField(default=False)
