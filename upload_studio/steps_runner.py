import json
import traceback

from django.db import transaction

from upload_studio.executor_registry import ExecutorRegistry
from upload_studio.models import Project, ProjectStepError


class StepsRunner:
    def __init__(self, project):
        self.project = project

    def _run_one_guarded(self, step):
        step.status = Project.STATUS_RUNNING
        step.save(using='control', update_fields=('status',))
        with transaction.atomic():
            prev_step = None
            if self.project.current_step > 0:
                prev_step = self.project.steps[self.project.current_step - 1]
                step.metadata_json = prev_step.metadata_json

            executor_class = ExecutorRegistry.get_executor(step.executor_name)
            executor = executor_class(
                project=self.project,
                step=step,
                prev_step=prev_step,
                **json.loads(step.executor_kwargs),
            )
            executor.run()

    def run_one(self):
        step = self.project.steps[self.project.current_step]
        try:
            self._run_one_guarded(step)
        except Exception as ex:
            with transaction.atomic():
                step.projectsteperror_set.all().delete()
                ProjectStepError.objects.create(
                    step=step,
                    message=traceback.format_exc(),
                )
                step.status = Project.STATUS_ERRORS
                step.save()
        return step

    def run_all(self):
        while True:
            step = self.run_one()
            if step.status != Project.STATUS_COMPLETE:
                break
            self.project.current_step += 1
            self.project.save()


StepsRunner(Project())
