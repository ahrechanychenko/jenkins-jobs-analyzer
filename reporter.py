from utils import get_jobs_from_yaml
from utils import get_job_instances
from utils import get_instance_last_builds_numbers
from utils import check_builds_result
from utils import send_mail
from utils import get_db_builds_number
from utils import create_database
from utils import update_db
import settings

if __name__ == '__main__':

    job_from_yaml = get_jobs_from_yaml(settings.JENKINS_JOBS_YAML)
    instances = get_job_instances(host=settings.JENKINS_HOST,
                                  jobs=job_from_yaml)
    instance_last_builds = get_instance_last_builds_numbers(instances,
                                                            job_from_yaml)
    db_con = settings.database

    if settings.init_run:
        create_database(settings.database, job_from_yaml)
        update_db(db_con, instances, job_from_yaml, init=True)

        failed_jobs = check_builds_result(db_con,
                                          job_from_yaml,
                                          instance_last_builds)
    else:
        db_builds = get_db_builds_number(db_con, job_from_yaml)
        update_db(db_con, instances, job_from_yaml, builds_in_db=db_builds)
        failed_jobs = check_builds_result(db_con,
                                          job_from_yaml,
                                          last_builds=None,
                                          db_previous_builds=db_builds)

    if failed_jobs:
        send_mail(list_of_failed_jobs=failed_jobs,
                  sender=settings.sender,
                  reciever=settings.receiver,
                  password=settings.password,
                  smtp_server=settings.smtp_server)
