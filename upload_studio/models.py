import json
import os
import shutil

from django.conf import settings
from django.db import models, transaction

from upload_studio.exceptions import ProjectFinishedException


class Project(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_WARNINGS = 'warnings'
    STATUS_ERRORS = 'errors'
    STATUS_COMPLETE = 'complete'
    STATUS_FINISHED = 'finished'
    STATUS_CHOICES = (
        (STATUS_PENDING, STATUS_PENDING),
        (STATUS_RUNNING, STATUS_RUNNING),
        (STATUS_WARNINGS, STATUS_WARNINGS),
        (STATUS_ERRORS, STATUS_ERRORS),
        (STATUS_COMPLETE, STATUS_COMPLETE),
        (STATUS_FINISHED, STATUS_FINISHED),
    )

    MEDIA_TYPE_MUSIC = 'music'
    MEDIA_TYPE_CHOICES = (
        (MEDIA_TYPE_MUSIC, MEDIA_TYPE_MUSIC),
    )

    name = models.CharField(max_length=1024)
    media_type = models.CharField(max_length=64, choices=MEDIA_TYPE_CHOICES)
    is_finished = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._steps = None

    def __str__(self):
        return 'Project(id={}, name={})'.format(self.id, self.name)

    @property
    def steps(self):
        if self._steps is None:
            self._steps = list(self.projectstep_set.order_by('index').all())
        return self._steps

    def raise_if_finished(self):
        if self.is_finished:
            raise ProjectFinishedException()

    @property
    def next_step(self):
        for step in self.steps:
            if step.status in {self.STATUS_PENDING, self.STATUS_WARNINGS, self.STATUS_ERRORS, self.STATUS_RUNNING}:
                return step
            elif step.status == self.STATUS_COMPLETE:
                continue
            elif step.status == self.STATUS_FINISHED:
                return None
        return None

    def save_steps(self):
        for index, step in enumerate(self.steps):
            step.project = self
            step.index = index
            step.save()

    @property
    def status(self):
        if self.is_finished:
            return self.STATUS_FINISHED
        next_step = self.next_step
        if next_step:
            return next_step.status
        return self.STATUS_COMPLETE

    @property
    def data_path(self):
        return os.path.join(settings.MEDIA_ROOT, 'upload_project_{}'.format(self.id))

    @transaction.atomic()
    def reset(self, step_index=0):
        self.raise_if_finished()
        for step in self.steps[step_index:]:
            step.status = self.STATUS_PENDING
            try:
                shutil.rmtree(step.path)
            except FileNotFoundError:
                pass
            step.reset_messages()
        self.save_steps()
        if step_index == 0:
            try:
                os.rmdir(self.data_path)
            except FileNotFoundError:
                pass


class ProjectStep(models.Model):
    project = models.ForeignKey(Project, models.CASCADE)
    index = models.IntegerField()
    status = models.CharField(max_length=64, choices=Project.STATUS_CHOICES, default=Project.STATUS_PENDING)
    executor_name = models.CharField(max_length=64)
    executor_kwargs_json = models.TextField(default='{}')
    metadata_json = models.TextField()

    @property
    def executor_kwargs(self):
        return json.loads(self.executor_kwargs_json)

    @executor_kwargs.setter
    def executor_kwargs(self, value):
        self.executor_kwargs_json = json.dumps(value)

    @property
    def description(self):
        from upload_studio.executor_registry import ExecutorRegistry
        kwargs = json.loads(self.executor_kwargs_json)
        return ExecutorRegistry.get_executor(self.executor_name).description.format(**kwargs)

    @property
    def path(self):
        return os.path.join(self.project.data_path, 'step_{}'.format(self.id))

    def get_area_path(self, area_name):
        return os.path.join(self.path, area_name)

    @property
    def data_path(self):
        return self.get_area_path('data')

    def reset_messages(self):
        self.projectstepwarning_set.all().delete()
        self.projectsteperror_set.all().delete()


class ProjectStepWarning(models.Model):
    step = models.ForeignKey(ProjectStep, models.CASCADE)
    message = models.TextField(unique=True)
    acked = models.BooleanField(default=False)


class ProjectStepError(models.Model):
    step = models.ForeignKey(ProjectStep, models.CASCADE)
    message = models.TextField()
