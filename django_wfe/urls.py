from django.urls import path, include
from rest_framework import routers
from . import views

app_name = "rest_framework"

router = routers.DefaultRouter()
router.register(r"steps", views.StepViewSet)
router.register(r"workflows", views.WorkflowViewSet)
router.register(r"jobs", views.JobViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("jobs/<int:job_id>/logs", views.JobLogsView.as_view(), name="job_logs"),
]
