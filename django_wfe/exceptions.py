from django.core.exceptions import ValidationError


# base exception classes:


class WFEException(Exception):
    pass


class RuntimeWFEError(WFEException):
    pass


class ValidationWFEError(ValidationError, WFEException):
    pass


# specific exceptions:


class FinishedWorkflow(WFEException):
    pass


class InputRequired(WFEException):
    pass


class WrongState(RuntimeWFEError):
    pass


class WorkflowDeleted(ValidationWFEError):
    pass
