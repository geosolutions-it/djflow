from rest_framework import viewsets, mixins, permissions
from django_wfe import order_workflow_execution

from .models import Step, Job, Workflow
from .serializers import StepSerializer, JobSerializer, WorkflowSerializer


class StepViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Step.objects.all()
    serializer_class = StepSerializer
    permission_classes = [permissions.AllowAny]


class WorkflowViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    permission_classes = [permissions.AllowAny]


class JobViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        # Job creation with REST API also orders Job's execution
        order_workflow_execution(serializer.validated_data["workflow_id"])
