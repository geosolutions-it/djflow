from rest_framework import serializers
from django.urls import reverse_lazy

from .models import Job, Workflow


class WorkflowSerializer(serializers.ModelSerializer):
    """
    WDK Workflow database representation serializer
    """

    class Meta:
        model = Workflow
        fields = "__all__"
        read_only_fields = ["name", "path"]


class JobSerializer(serializers.ModelSerializer):
    """
    WDK Workflow's execution (Job's) database representation serializer
    """

    workflow = WorkflowSerializer(read_only=True)
    workflow_id = serializers.IntegerField(write_only=True)
    log_file = serializers.SerializerMethodField()

    class Meta:
        model = Job
        exclude = ["logfile", "uuid"]
        read_only_fields = [
            "current_step",
            "current_step_number",
            "storage",
            "state",
            "uuid",
            "logfile",
            "logs",
        ]

    def get_log_file(self, obj):
        return reverse_lazy("django_wfe:job_logs", args=[obj.id])
