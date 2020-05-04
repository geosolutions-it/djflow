from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r"steps", views.StepViewSet)
router.register(r"workflows", views.WorkflowViewSet)
router.register(r"jobs", views.JobViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]
