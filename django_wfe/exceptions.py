class WFEException(Exception):
    pass


class FinishedWorkflow(WFEException):
    pass


class InputRequired(WFEException):
    pass


class RuntimeWFEError(WFEException):
    pass


class WrongState(RuntimeWFEError):
    pass
