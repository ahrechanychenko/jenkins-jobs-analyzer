import os

from utils import get_jobs_from_yaml
from utils import get_job_instances
from utils import get_instance_last_build_number
from utils import check_last_build_result
from utils import open_db_conn
from utils import send_mail
from utils import get_db_builds_number
from utils import create_database
from utils import update_db
import settings

if __name__ == '__main__':

    job_from_yaml = get_jobs_from_yaml(settings.JENKINS_JOBS_YAML)
    instances = get_job_instances(host=settings.JENKINS_HOST, jobs=job_from_yaml)
    jobs_build_numbers = get_instance_last_build_number(instances, job_from_yaml)
    db_con = settings.database

    if settings.init_run:
        create_database(settings.database, job_from_yaml)
        update_db(db_con, instances, job_from_yaml, init=True)
        failed_jobs = check_last_build_result(job_from_yaml,
                                              jobs_build_numbers, settings.database)
    else:
        db_builds = get_db_builds_number(db_con, job_from_yaml)
        print db_builds
        update_db(db_con, instances, job_from_yaml, db_builds)
        failed_jobs = check_last_build_result(db_con, job_from_yaml, jobs_build_numbers,
                            db_builds)

    if failed_jobs:
        send_mail(list_of_failed_jobs=failed_jobs,
                  sender=settings.sender,
                  reciever=settings.reciever,
                  password=settings.password,
                  smtp_server=settings.smtp_server)