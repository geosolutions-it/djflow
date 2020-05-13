from rest_framework import serializers
from django.urls import reverse_lazy
from django.utils.html import format_html

from .models import Job, Workflow, Step


class StepSerializer(serializers.ModelSerializer):
    """
    WDK Step database representation serializer
    """

    class Meta:
        model = Step
        fields = "__all__"
        read_only_fields = ["name", "path"]


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
    current_step = StepSerializer(read_only=True)
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
