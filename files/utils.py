import jenkins
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import yaml
import sqlite3
import re


def pretty_log(src, indent=0, invert=False):
    """ Make log more readable and awesome
    The main application is using instead of json.dumps().
    :param src: dictionary with data, list of dicts
                can be also used for strings or lists of strings,
                but it makes no sense.
                Note: Indent for list by default is +3. If you want to call
                pretty_log for list , call it with indent=-3 for 0,
                indent=-3+1 for 1 and etc.
    :param indent: int
    :param invert: Swaps first and second columns. Can be used ONLY
     with one levels dictionary
    :return: formatted string with result, can be used in log
    """

    result = ''
    templates = ["\n{indent}{item:{len}}{value}" if not invert else
                 "\n{indent}{value:{len}}{item}",
                 "\n{indent}{item}:",
                 '\n{indent}{value}']

    if src and isinstance(src, dict):
        max_len = len(max(src.values() if invert else src.keys(),
                          key=lambda x: len(str(x))))
        for key, value in src.items():
            if (isinstance(value, dict) and value) or \
                    isinstance(value, list):
                result += templates[1].format(indent=' ' * indent, item=key)
                result += pretty_log(value, indent + 3)
            else:
                result += templates[0].format(indent=' ' * indent,
                                              item=key,
                                              value=str(value),
                                              len=max_len + 5)

    elif src and isinstance(src, list):
        for el in src:
            if (isinstance(el, dict) and el) or isinstance(el, list):
                res = pretty_log(el, indent + 3)
            else:
                res = templates[2].format(indent=' ' * (indent + 3),
                                          value=str(el))
            result += res[:indent + 2] + '-' + res[indent + 3:]
    return result


def get_instance_last_builds_numbers(job_instances, jobs):
    """return last execute build number for job
    :param job_instances: jenkins_job_instances from get_job_instances method
    :param jobs: list of jobs executed retrieved from get_jobs_from_yaml method
    :return: dict with 'job':int_build_number
    """

    jobs_last_builds = {}
    for job_name in jobs:
        jobs_last_builds[job_name] = \
            job_instances[job_name]['lastCompletedBuild']['number']

    return jobs_last_builds


def get_jobs_from_yaml(JENKINS_JOBS_YAML):
    """ retrieve jenkins job's from yaml
    :param JENKINS_JOBS_YAML: yaml file with list of jenkins jobs
    :return: list with jobs
    """

    with open(JENKINS_JOBS_YAML, "r") as f:
        jobs = yaml.load(f)
    return jobs


def get_job_instances(host, jobs):
    """ retrieve dict with full info of executed jenkins_jobs
    :param host: jenkins host from settings.JENKINS_HOST
    :param jobs: list of jobs executed retrieved from get_jobs_from_yaml method
    :return: dict with instances {job_name:instance,}
    """

    jenkins_url = 'http://' + host
    server = jenkins.Jenkins(jenkins_url)

    job_instances = {}

    for job_name in jobs:
        job_instances[job_name] = server.get_job_info(job_name, depth=10)

    return job_instances


def send_mail(list_of_failed_jobs, sender, reciever, password, smtp_server):
    fromaddr = sender
    toaddr = reciever
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "gating"
    body = "list of failed jobs \n {}".format(pretty_log(list_of_failed_jobs, indent=1))
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(smtp_server, 587)
    server.starttls()
    server.login(fromaddr, password)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()


def create_database(db, jobs):
    """ Create database and create schema for data
    :param db: string, name of database
    :param jobs: list of jobs executed retrieved from get_jobs_from_yaml method
    """

    con = open_db_conn(db)
    cur = con.cursor()
    for job in jobs:
        job = re.sub('[-.]', '_', job).rsplit('_', 5)[0]
        table_exist = cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name=?", (job,))
        if not table_exist.fetchone():
            cur.execute('CREATE TABLE  ' + job +
                        ' (build_number INT, '
                        'result VARCHAR(30),url VARCHAR(30))')

    con.commit()
    con.close()


def sql_job_lenght_limit(job):
    """ Remove SQL not supported chars from jobs names
    and limit name name lenght
    :param job: name of job
    :return: correct job name
    """

    job_name = re.sub('[-.]', '_', job).rsplit('_', 5)[0]
    return job_name


def check_builds_result(db, jobs, last_builds=None, db_previous_builds=None):
    """ check builds results stored in db
    :param db: db connection's from open_db_conn method
    :param jobs: list of jobs executed retrieved from get_jobs_from_yaml method
    :param last_builds: dict from get_instance_last_builds_numbers
    :param db_previous_builds: dict from get_db_builds_numbers
    :return: dict of failed jobs if they present in db
    """

    failed_jobs = {}
    db_builds = get_db_builds_number(db, jobs)
    for job in jobs:
        if last_builds:
            con = open_db_conn(db)
            cur = con.cursor()

            cur.execute(
                'SELECT result from ' + sql_job_lenght_limit(
                    job) + ' WHERE build_number=?', (last_builds[job],))

            result = cur.fetchall()

            if 'FAILURE' in result:
                con = open_db_conn(db)
                cur = con.cursor()
                failed_jobs[job] = {}
                failed_jobs[job]['result'] = result

                cur.execute('SELECT url from ' + sql_job_lenght_limit(
                    job) + ' WHERE build_number=?',
                            (last_builds[job],))

                url = cur.fetchall()
                failed_jobs[job]['url'] = url

        elif db_previous_builds:
            for build in db_builds[sql_job_lenght_limit(job)]:
                if build not in db_previous_builds[sql_job_lenght_limit(job)]:
                    con = open_db_conn(db)
                    cur = con.cursor()

                    cur.execute(
                        'SELECT result from ' + sql_job_lenght_limit(
                            job) + ' WHERE build_number=?', (build,))

                    result = cur.fetchall()
                    if 'FAILURE' in result:
                        failed_jobs[job] = {}
                        failed_jobs[job]['result'] = result
                        con = open_db_conn(db)
                        cur = con.cursor()

                        cur.execute(
                            'SELECT url from ' + sql_job_lenght_limit(
                                job) + ' WHERE build_number=?', (build,))

                        url = cur.fetchall()
                        failed_jobs[job]['url'] = url

    return failed_jobs


def get_db_builds_number(db, jobs):
    """ Return dict with builds for jobs stored in db
    :param db: db connection's from open_db_conn method
    :param jobs: list of jobs executed retrieved from get_jobs_from_yaml method
    :return: dict {'job':[builds]}
    """

    builds = {}
    for job in jobs:
        job = sql_job_lenght_limit(job)
        con = open_db_conn(db)
        cur = con.cursor()

        cur.execute('SELECT build_number from ' + job)

        select = cur.fetchall()
        con.close()
        builds[job] = select

    return builds


def open_db_conn(db):
    """ Connect to db and return con instance
    :param db: name of db
    :return: connection instance
    """

    con = sqlite3.connect(db)
    con.row_factory = lambda cursor, row: row[0]
    return con


def update_db(db, instance, jobs, builds_in_db=None, init=False):
    """ Add results of jobs to db
    :param db: db connection's from open_db_conn method
    :param jobs: list of jobs executed retrieved from get_jobs_from_yaml method
    :param instance: instances from get_job_instances method
    :param builds_in_db: dict from get_db_builds_numbers
    :param init: if init - write only last build's from instances
    """

    for job in jobs:

        if init:
            result = instance[job]['lastCompletedBuild']['result']
            url = instance[job]['lastCompletedBuild']['url']
            number = instance[job]['lastCompletedBuild']['number']
            con = open_db_conn(db)
            cur = con.cursor()

            cur.execute(
                'INSERT INTO ' + sql_job_lenght_limit(job) + ' (build_number ,'
                                                             ' result, url'
                                                             ') '
                                                             'VALUES '
                                                             '(?, ?, ?)',
                (number, result, url))
            con.commit()
            con.close()

        else:
            for i in range(len(instance[job]['builds'])):
                url = instance[job]['builds'][i]['url']
                result = instance[job]['builds'][i]['result']
                number = instance[job]['builds'][i]['number']
                if result:
                    if number not in builds_in_db[sql_job_lenght_limit(job)]:
                        # remove after finish testing
                        print number, builds_in_db[sql_job_lenght_limit(job)], sql_job_lenght_limit(job)
                        con = open_db_conn(db)
                        cur = con.cursor()

                        db_job = sql_job_lenght_limit(job)

                        cur.execute(
                            "INSERT INTO " + db_job + " (build_number ,"
                                                      "result, url)"
                                                      " VALUES (?, ?, ?)",
                            (number, result, url))
                        con.commit()
                        con.close()
                    if number in builds_in_db[sql_job_lenght_limit(job)]:
                        break
