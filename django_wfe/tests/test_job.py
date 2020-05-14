import os
import pydantic
import tempfile
from django.test import TestCase, override_settings

from django_wfe.models import Step, Workflow, Job, JobState
from django_wfe import steps
from django_wfe import workflows
from django_wfe import exceptions


@override_settings(WFE_WORKFLOWS="django_wfe.tests.wdf_models")
class JobTest(TestCase):

    fixtures = [
        "django_wfe/tests/wdk_fixtures.json",
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # create the temporary log directory
        cls.tmp_log_dir = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        # remove temporary log dir
        cls.tmp_log_dir.cleanup()

    def test_import_class(self):
        step = Step.objects.first()
        StepClass = Job.import_class(step.path)

        self.assertTrue(
            isinstance(StepClass, steps.StepType),
            f"Imported StepClass is not a StepType type",
        )

    def test_run_next_content(self):
        """
        Test Job._run_next() method's content on an empty Step from TestWorkflowEmpty workflow
        """
        workflow = Workflow.objects.get(name="TestWorkflowEmpty")

        job = Job(
            workflow_id=workflow.id,
            logfile=os.path.join(self.tmp_log_dir.name, "django_wfe_tmp.log"),
        )
        job.save()

        self.assertEqual(
            job.state,
            JobState.PENDING,
            f"Initial Job state is different from JobState.PENDING: {job.state}",
        )
        self.assertEqual(
            job.current_step.id,
            Step.objects.get(name="__start__").id,
            f"Initial Job step wasn't updated with __start__ step",
        )

        # import Step and Workflow Classes
        WorkflowClass = job.import_class(job.workflow.path)
        self.assertTrue(
            isinstance(WorkflowClass, workflows.WorkflowType),
            f"Imported StepClass is not a StepType type",
        )

        StepClass = job.import_class(job.current_step.path)
        self.assertTrue(
            isinstance(StepClass, steps.StepType),
            f"Imported StepClass is not a StepType type",
        )

        # initialize the first step
        current_step = job._step_initialize(StepClass)

        # refresh the Job model
        job.refresh_from_db()

        self.assertEqual(
            job.state,
            JobState.ONGOING,
            f"Expected Job state to be JobState.ONGOING, after __start__ Step initialization",
        )
        self.assertTrue(
            isinstance(current_step, steps.__start__),
            f"First Step should be an instance of __start__ Step class",
        )

        # execute the first step
        result = job._step_execute(current_step)

        # refresh the Job model
        job.refresh_from_db()

        self.assertIsNone(result, f"The __start__ step shouldn't return any result")
        self.assertIsNone(
            job.storage["data"][job.current_step_number]["result"],
            f"The __start__ step's 'None' result should be serialized to the DB storate",
        )

        # calculate transition of the first step
        transition = job._step_calculate_transition(current_step)

        # refresh the Job model
        job.refresh_from_db()

        self.assertEqual(
            transition,
            0,
            f"The __start__ step should return index 0 for the next transition, instead got: {transition}",
        )

        with self.assertRaises(exceptions.FinishedWorkflow):
            job._workflow_transition(WorkflowClass, StepClass, transition)

    def test_execute_empty_workflow(self):
        """
        Test Job.execute() method on TestWorkflowEmpty workflow
        """
        workflow = Workflow.objects.get(name="TestWorkflowEmpty")

        job = Job(
            workflow_id=workflow.id,
            logfile=os.path.join(self.tmp_log_dir.name, "django_wfe_tmp.log"),
        )
        job.save()

        job.execute()

        # refresh the Job model
        job.refresh_from_db()

        self.assertEqual(
            job.state,
            JobState.FINISHED,
            f"Expected Job state to be JobState.FINISHED, TestWorkflowEmpty execution",
        )
        self.assertEqual(job.current_step_number, 0)

    def test_execute_success_workflow(self):
        """
        Test Job.execute() method on TestWorkflowSuccess workflow
        """
        workflow = Workflow.objects.get(name="TestWorkflowSuccess")

        job = Job(
            workflow_id=workflow.id,
            logfile=os.path.join(self.tmp_log_dir.name, "django_wfe_tmp.log"),
        )
        job.save()

        job.execute()

        # refresh the Job model
        job.refresh_from_db()

        self.assertEqual(
            job.state,
            JobState.FINISHED,
            f"Expected Job state to be JobState.FINISHED, TestWorkflowSuccess execution",
        )
        self.assertEqual(
            job.current_step_number,
            3,
            "Not all steps of the TestWorkflowSuccess were executed",
        )

    def test_execute_error_workflow(self):
        """
        Test Job.execute() method on TestWorkflowError workflow
        """
        workflow = Workflow.objects.get(name="TestWorkflowError")

        job = Job(
            workflow_id=workflow.id,
            logfile=os.path.join(self.tmp_log_dir.name, "django_wfe_tmp.log"),
        )
        job.save()

        job.execute()

        # refresh the Job model
        job.refresh_from_db()

        self.assertEqual(
            job.state,
            JobState.FAILED,
            f"Expected Job state to be JobState.FAILED, TestWorkflowError execution",
        )
        self.assertEqual(
            job.current_step_number,
            2,
            "Not all steps of the TestWorkflowError were executed",
        )

    def test_execute_input_workflow(self):
        """
        Test Job.execute() method on TestWorkflowExternalInput workflow
        """
        workflow = Workflow.objects.get(name="TestWorkflowExternalInput")

        job = Job(
            workflow_id=workflow.id,
            logfile=os.path.join(self.tmp_log_dir.name, "django_wfe_tmp.log"),
        )
        job.save()

        job.execute()

        # refresh the Job model
        job.refresh_from_db()

        self.assertEqual(
            job.state,
            JobState.INPUT_REQUIRED,
            f"Expected Job state to be JobState.INPUT_REQUIRED, TestWorkflowExternalInput execution",
        )
        self.assertEqual(
            job.current_step_number,
            2,
            "Not all steps of the TestWorkflowExternalInput were executed",
        )

    def test_provide_external_input_success(self):
        """
        Test Job.provide_external_input() method on TestWorkflowExternalInput workflow
        """
        workflow = Workflow.objects.get(name="TestWorkflowExternalInput")

        # mock Job's state before providing external data
        job = Job(
            workflow_id=workflow.id,
            current_step_id=Step.objects.get(name="ExternalInputStep").id,
            current_step_number=2,
            storage={
                "data": [
                    {"step": Step.objects.get(name="__start__").name, "result": None},
                    {"step": Step.objects.get(name="EmptyStepA").name, "result": None},
                ]
            },
            state=JobState.INPUT_REQUIRED,
            logfile=os.path.join(self.tmp_log_dir.name, "django_wfe_tmp.log"),
        )
        job.save()

        external_data = {"external_int": 1}
        job.provide_external_input(external_data)

        # refresh the Job model
        job.refresh_from_db()

        self.assertEqual(
            job.state,
            JobState.INPUT_RECEIVED,
            "Expected Job state to be JobState.INPUT_RECEIVED",
        )
        self.assertEqual(
            job.storage["data"][job.current_step_number]["external_data"],
            {"external_int": 1},
        )

    def test_provide_external_input_error(self):
        """
        Test Job.provide_external_input() method on TestWorkflowExternalInput workflow
        """
        workflow = Workflow.objects.get(name="TestWorkflowExternalInput")

        # mock Job's state before providing external data
        job = Job(
            workflow_id=workflow.id,
            current_step_id=Step.objects.get(name="ExternalInputStep").id,
            current_step_number=2,
            storage={
                "data": [
                    {"step": Step.objects.get(name="__start__").name, "result": None},
                    {"step": Step.objects.get(name="EmptyStepA").name, "result": None},
                ]
            },
            state=JobState.INPUT_REQUIRED,
            logfile=os.path.join(self.tmp_log_dir.name, "django_wfe_tmp.log"),
        )
        job.save()

        external_data = {"external_int": dict()}

        with self.assertRaises(pydantic.ValidationError):
            job.provide_external_input(external_data)

        # refresh the Job model
        job.refresh_from_db()

        self.assertEqual(
            job.state,
            JobState.INPUT_REQUIRED,
            "Expected Job state to be JobState.INPUT_RECEIVED",
        )
        with self.assertRaises(IndexError):
            serialized_input = job.storage["data"][job.current_step_number][
                "external_data"
            ]

    def test_execute_after_receiving_input(self):
        """
        Test Job.execute() method on TestWorkflowExternalInput workflow after receiving External Input
        """
        workflow = Workflow.objects.get(name="TestWorkflowExternalInput")

        external_int = 1

        # mock Job's state before providing external data
        job = Job(
            workflow_id=workflow.id,
            current_step_id=Step.objects.get(name="ExternalInputStep").id,
            current_step_number=2,
            storage={
                "data": [
                    {"step": Step.objects.get(name="__start__").name, "result": None},
                    {"step": Step.objects.get(name="EmptyStepA").name, "result": None},
                    {
                        "step": Step.objects.get(name="ExternalInputStep").name,
                        "external_data": {"external_int": external_int},
                    },
                ]
            },
            state=JobState.INPUT_RECEIVED,
            logfile=os.path.join(self.tmp_log_dir.name, "django_wfe_tmp.log"),
        )
        job.save()

        # resume Job execution
        job.execute()

        # refresh the Job model
        job.refresh_from_db()

        self.assertEqual(
            job.state, JobState.FINISHED, "Expected Job state to be JobState.FINISHED"
        )
        self.assertEqual(
            job.current_step_number,
            3,
            "Not all steps of the TestWorkflowExternalInput were executed",
        )
        self.assertEqual(
            job.storage["data"][2]["result"],
            external_int,
            "ExternalInputStep didn't return expected value",
        )
