import logging
import dramatiq
from typing import Union

from django.db.models import ObjectDoesNotExist
from .models import Job

logger = logging.getLogger(__name__)


@dramatiq.actor(max_retries=1)
def process_job(job_id: Union[str, int]):
    """
    Job's (Workflow execution) monitor for Django WFE.

    :param job_id: django_wfe.models.Job ID
    """

    try:
        job = Job.objects.get(id=int(job_id))
    except ObjectDoesNotExist:
        logger.error(
            f"A job with provided ID ({job_id}) does not exist in the database."
        )
        raise Exception("Job with provided ID does not exist in the database.")

    job.execute()
