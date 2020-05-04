class WorkflowType(type):
    """
    WDK Workflow type class
    """

    pass


class Workflow(metaclass=WorkflowType):
    """
    Base class for user defined WKD Workflows
    """

    DIGRAPH = None
