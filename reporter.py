import os

from files.utils import get_jobs_from_yaml
from files.utils import get_job_instances
from files.utils import get_instance_last_builds_numbers
from files.utils import check_builds_result
from files.utils import send_mail
from files.utils import get_db_builds_number
from files.utils import create_database
from files.utils import update_db
from files import settings

if __name__ == '__main__':

    job_from_yaml = get_jobs_from_yaml(settings.JENKINS_JOBS_YAML)
    instances = get_job_instances(host=settings.JENKINS_HOST,
                                  jobs=job_from_yaml)
    instance_last_builds = get_instance_last_builds_numbers(instances,
                                                            job_from_yaml)
    db = settings.database
    db_exist = os.path.isfile(db)

    if db_exist:
        db_builds = get_db_builds_number(db, job_from_yaml)
        update_db(db, instances, job_from_yaml, builds_in_db=db_builds)
        failed_jobs = check_builds_result(db,
                                          job_from_yaml,
                                          last_builds=None,
                                          db_previous_builds=db_builds)

    else:
        create_database(settings.database, job_from_yaml)
        update_db(db, instances, job_from_yaml, init=True)

        failed_jobs = check_builds_result(db,
                                          job_from_yaml,
                                          instance_last_builds)

    if failed_jobs:
        send_mail(list_of_failed_jobs=failed_jobs,
                  sender=settings.sender,
                  reciever=settings.receiver,
                  password=settings.password,
                  smtp_server=settings.smtp_server)
