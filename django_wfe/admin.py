from django.urls import reverse_lazy
from django.contrib import admin
from django.utils.html import format_html


from .tasks import process_job
from .models import Step, Workflow, Job


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ("name", "path")
    list_filter = ("name", "path")
    search_fields = ("name",)

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "path")
    list_filter = ("name", "path")
    search_fields = ("name",)

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("__str__", "workflow", "state", "logs")
    list_filter = ("workflow", "state")
    search_fields = ("workflow__path", "state")
    readonly_fields = ("current_step", "storage", "state", "logfile")
    exclude = ("uuid",)

    def logs(self, obj):
        return format_html(
            f"<a href='{reverse_lazy('django_wfe:job_logs', args=[obj.id])}'>{obj}</a>"
        )

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # saving a Jobs instance in the Django Admin Panel also starts the Job execution
        process_job.send(obj.id)
