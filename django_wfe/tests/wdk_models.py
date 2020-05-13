from random import randint
from django_wfe import steps, workflows
from pydantic import BaseModel


class EmptyStepA(steps.Step):
    def execute(self, _input=None, external_input=None, *args, **kwargs):
        pass


class EmptyStepB(steps.Step):
    def execute(self, _input=None, *args, **kwargs):
        pass


class EmptyStepC(steps.Step):
    def execute(self, _input=None, *args, **kwargs):
        pass


class EmptyStepD(steps.Step):
    def execute(self, _input=None, *args, **kwargs):
        pass


class RandomIntStep(steps.Step):
    def execute(self, _input=None, external_input=None, *args, **kwargs):
        return randint(0, 1)


class ExternalInputStep(steps.Step):
    class UserInputSchema(BaseModel):
        external_int: int

    def execute(self, _input=None, external_input=None, *args, **kwargs):
        print(external_input["external_int"])
        return external_input["external_int"]


class ErrorStep(steps.Step):
    def execute(self, _input=None, external_input=None, *args, **kwargs):
        raise Exception("Some exception")


class Decision(steps.Decision):
    def transition(self, _input=None, *args, **kwargs):
        return _input


class TestWorkflowSuccess(workflows.Workflow):

    DIGRAPH = {
        steps.__start__: [EmptyStepA],
        EmptyStepA: [EmptyStepB],
        EmptyStepB: [EmptyStepC],
    }


class TestWorkflowError(workflows.Workflow):

    DIGRAPH = {
        steps.__start__: [EmptyStepA],
        EmptyStepA: [ErrorStep],
    }


class TestWorkflowExternalInput(workflows.Workflow):

    DIGRAPH = {
        steps.__start__: [EmptyStepA],
        EmptyStepA: [ExternalInputStep],
        ExternalInputStep: [EmptyStepB],
    }


class TestWorkflowDecision(workflows.Workflow):

    DIGRAPH = {
        steps.__start__: [RandomIntStep],
        RandomIntStep: [Decision],
        Decision: [EmptyStepA, EmptyStepB],
        EmptyStepA: [EmptyStepC],
        EmptyStepB: [EmptyStepC],
    }


class TestWorkflowEmpty(workflows.Workflow):

    DIGRAPH = {
        steps.__start__: [],
    }
