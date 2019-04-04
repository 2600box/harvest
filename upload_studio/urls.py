from django.urls import path

from . import views

urlpatterns = [
    path('projects', views.Projects.as_view()),
    path('projects/<pk>', views.ProjectView.as_view()),
    path('projects/<pk>/reset-to-step', views.ProjectResetToStep.as_view()),
    path('projects/<pk>/run-all', views.ProjectRunAll.as_view()),
    path('projects/<pk>/run-one', views.ProjectRunOne.as_view()),
    path('projects/<pk>/warnings/<warning_id>/ack', views.WarningAck.as_view()),
]
