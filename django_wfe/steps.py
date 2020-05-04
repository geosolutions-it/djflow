from typing import Dict
from pydantic import BaseModel


class StepType(type):
    """
    WDK Step and Decision type class
    """

    pass


class BaseStep(metaclass=StepType):
    """
    Base class for WKD Steps and Decisions
    """

    user_input_schema = None

    class UserInputSchema(BaseModel):
        pass

    def __init__(self, job=None):
        self.job = job

    def execute(self, _input=None, *args, **kwargs):
        raise NotImplementedError

    def transition(self, *args, **kwargs):
        raise NotImplementedError

    def _perform_execute(self, _input=None, *args, **kwargs):
        # pass external_input to the user defined execute() method
        try:
            external_input = self.job.storage["data"][self.job.current_step_number][
                "external_data"
            ]
        except (KeyError, IndexError):
            external_input = None

        return self.execute(_input, external_input=external_input, *args, **kwargs)

    def _perform_transition(self, _input=None, *args, **kwargs):
        # pass external_input to the user defined transition() method
        try:
            external_input = self.job.storage["data"][self.job.current_step_number][
                "external_data"
            ]
        except (KeyError, IndexError):
            external_input = None

        return self.transition(_input, external_input=external_input, *args, **kwargs)

    @property
    def requires_input(self):
        # check if UserInputSchema defines any structure
        if self.UserInputSchema.__fields__:
            return True

        return False


class Step(BaseStep):
    """
    Base class for user defined WKD Steps
    """

    def execute(self, _input=None, external_input=None, *args, **kwargs):
        raise NotImplementedError

    def transition(self, _input=None, external_input=None, *args, **kwargs):
        return 0


class Decision(BaseStep):
    """
    Base class for user defined WKD Decisions
    """

    def execute(self, _input=None, external_input=None, *args, **kwargs):
        return

    def transition(self, _input=None, external_input=None, *args, **kwargs):
        raise NotImplementedError


class __start__(Step):
    """
    The first step of the Workflow, to mark where Workflow execution should begin.

    __start__ step allows only one outgoing graph's edge (transition is always
    performed to the 1st defined node).
    """

    def execute(self, input: Dict = None, external_input: Dict = None, *args, **kwargs):
        return

    def transition(self, _input=None, external_input: Dict = None, *args, **kwargs):
        return 0
