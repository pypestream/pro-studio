import sys
from unittest.mock import patch

import pytest

from baserow.core.jobs.exceptions import JobDoesNotExist, MaxJobCountExceeded
from baserow.core.jobs.handler import JobHandler
from baserow.core.jobs.models import Job
from baserow.core.jobs.registries import JobType, job_type_registry


@pytest.mark.django_db(transaction=True)
@patch("baserow.core.jobs.handler.run_async_job")
def test_create_and_start_job(mock_run_async_job, data_fixture):
    data_fixture.register_temp_job_types()

    user = data_fixture.create_user()

    job = JobHandler().create_and_start_job(user, "tmp_job_type_1")
    assert job.user_id == user.id
    assert job.progress_percentage == 0
    assert job.state == "pending"
    assert job.error == ""

    mock_run_async_job.delay.assert_called_once()
    args = mock_run_async_job.delay.call_args
    assert args[0][0] == job.id


@pytest.mark.django_db(transaction=True)
@patch("baserow.core.jobs.handler.run_async_job")
def test_create_and_start_job_with_system_exit(mock_run_async_job, data_fixture):
    data_fixture.register_temp_job_types()

    user = data_fixture.create_user()

    # Simulate a SystemExit during the delay call
    mock_run_async_job.delay.side_effect = lambda x: sys.exit(-1)

    with pytest.raises(SystemExit):
        JobHandler().create_and_start_job(user, "tmp_job_type_1")

    job = Job.objects.first()
    assert job.user_id == user.id
    assert job.progress_percentage == 0
    assert job.state == "failed"
    assert job.error == "-1"


@pytest.mark.django_db
def test_exceeding_max_job_count(data_fixture):
    data_fixture.register_temp_job_types()

    user = data_fixture.create_user()

    # Max count is 3 for this job type
    JobHandler().create_and_start_job(user, "tmp_job_type_2")
    JobHandler().create_and_start_job(user, "tmp_job_type_2")
    JobHandler().create_and_start_job(user, "tmp_job_type_2")

    with pytest.raises(MaxJobCountExceeded):
        JobHandler().create_and_start_job(user, "tmp_job_type_2")


@pytest.mark.django_db
def test_get_job(data_fixture):
    user = data_fixture.create_user()

    job_1 = data_fixture.create_fake_job(user=user, type="tmp_job_type_1")
    job_2 = data_fixture.create_fake_job(type="tmp_job_type_1")

    with pytest.raises(JobDoesNotExist):
        JobHandler().get_job(user, job_2.id)

    job = JobHandler().get_job(user, job_1.id)
    assert isinstance(job, Job)
    assert job.id == job_1.id


@pytest.mark.django_db
def test_job_progress_changed_bug_regression(data_fixture):
    """
    Small regression test for an undefined variable in JobHandler.run
    """

    class IdlingJobType(JobType):
        type = "idling_job"
        model_class = Job

        def run(self, job, progress):
            return (
                job,
                progress,
            )

    with patch.object(job_type_registry, "registry", {}):
        job_type_registry.get_for_class.cache_clear()
        job_type_registry.register(IdlingJobType())

        user = data_fixture.create_user()

        job_1 = data_fixture.create_fake_job(user=user, type=IdlingJobType.type)

        _job, _progress = JobHandler().run(job_1)

        assert _job
        assert _progress

        _job.progress = 1
        _job.save()
        _progress.set_progress(1, None)
        assert _job.progress == 1
        # in old code this will fail with UnboundLocalError
        _progress.set_progress(1, None)
