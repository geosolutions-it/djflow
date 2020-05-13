from django.http import FileResponse
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import views, viewsets, mixins, permissions
from rest_framework.response import Response

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


class JobLogsView(views.APIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except ObjectDoesNotExist:
            return Response("Job not found", status=404)

        try:
            return FileResponse(open(job.logfile, "rb"))
        except FileNotFoundError:
            return Response("Log file not found", status=404)
