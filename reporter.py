import os

from helpers.utils import get_jobs_from_yaml
from helpers.utils import get_job_instances
from helpers.utils import get_instance_last_builds_numbers
from helpers.utils import check_for_failed_builds
from helpers.utils import check_for_skipped_modules
from helpers.utils import send_mail
from helpers.utils import get_db_builds_number
from helpers.utils import create_database
from helpers.utils import update_db
from files import settings


if __name__ == '__main__':
    # pylint: disable=C0103
    jobs = get_jobs_from_yaml(settings.JENKINS_JOBS_YAML)
    jenkins_instances = get_job_instances(host=settings.JENKINS_HOST,
                                          jobs=jobs)
    jenkins_instance_last_builds = get_instance_last_builds_numbers(
        jenkins_instances,
        jobs)
    db = settings.database
    db_exist = os.path.isfile(db)
    if db_exist:
        db_builds = get_db_builds_number(db, jobs)
        update_db(db, jenkins_instances, jobs, builds_in_db=db_builds)
        failed_jobs = check_for_failed_builds(db,
                                              jobs,
                                              last_builds=None,
                                              db_previous_builds=db_builds)
        skipped_modules = check_for_skipped_modules(
            db,
            jobs,
            last_builds=None,
            db_previous_builds=db_builds)

    else:
        create_database(settings.database, jobs)
        update_db(db, jenkins_instances, jobs, init=True)

        failed_jobs = check_for_failed_builds(db,
                                              jobs,
                                              jenkins_instance_last_builds)
        skipped_modules = check_for_skipped_modules(
            db,
            jobs,
            jenkins_instance_last_builds)
    if failed_jobs:
        send_mail(list_of_failed_jobs=failed_jobs,
                  sender=settings.sender,
                  reciever=settings.receiver,
                  password=settings.password,
                  smtp_server=settings.smtp_server)
    if skipped_modules:
        send_mail(list_of_failed_jobs=None,
                  sender=settings.sender,
                  reciever=settings.receiver,
                  password=settings.password,
                  smtp_server=settings.smtp_server,
                  skipped_modules=skipped_modules)
