from rest_framework import viewsets, mixins, permissions

from .models import Step, Job, Workflow
from .serializers import StepSerializer, JobSerializer, WorkflowSerializer
from .tasks import process_job


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
        job = serializer.save()
        # send Job's execution to Dramatiq on Job's creation
        process_job.send(job_id=job.id)
