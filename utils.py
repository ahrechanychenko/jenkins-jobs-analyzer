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


def get_instance_last_build_number(job_instances, jobs):
    jobs_last_builds = {}
    for job_name in jobs:
        jobs_last_builds[job_name] = \
            job_instances[job_name]['lastCompletedBuild']['number']
    return jobs_last_builds


def get_jobs_from_yaml(JENKINS_JOBS_YAML):
    # retrieve jenkins job's from yaml
    with open(JENKINS_JOBS_YAML, "r") as f:
        jobs = yaml.load(f)
    return jobs


def get_job_instances(host, jobs):
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
    body = "list of failed jobs \n {}".format(pretty_log(list_of_failed_jobs))
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(smtp_server, 587)
    server.starttls()
    server.login(fromaddr, password)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()


def create_database(db_con, jobs):
    cur = db_con.cursor()
    for job in jobs:
        job = re.sub('[-.]', '_', job)
        table_exist = cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name=?", (job,))
        if not table_exist.fetchone():
            cur.execute("CREATE TABLE  " + job +
                        " (build_number INT, "
                        "result VARCHAR(30),"
                        "url VARCHAR(30))")
    db_con.commit()
    db_con.close()


def check_last_build_result(db_con, jobs, jobs_build_numbers=None,
                            db_before_check_last_builds=None):
    cur = db_con.cursor()
    failed_jobs = {}
    for job in jobs:
        if jobs_build_numbers:
            cur.execute("SELECT result from " + (re.sub('[-.]', '_', job)) +
                        " WHERE build_number=?", (jobs_build_numbers[job], ))
            result = cur.fetchall()
            if 'FAILURE' in result:
                failed_jobs[job] = {}
                failed_jobs[job]['result'] = result
                cur.execute("SELECT url from " + (re.sub('[-.]', '_', job)) +
                            " WHERE build_number=?", (jobs_build_numbers[job],))
                url = cur.fetchall()
                failed_jobs[job]['url'] = url

        elif db_before_check_last_builds:
            db_builds = get_db_builds_number(db_con, jobs)
            for build in db_builds[job]:
                if build not in db_before_check_last_builds[job]:
                    cur.execute(
                        "SELECT result from " + (re.sub('[-.]', '_', job)) +
                        " WHERE build_number=?", (build,))
                result = cur.fetchall()
                if 'FAILURE' in result:
                    failed_jobs[job] = {}
                    failed_jobs[job]['result'] = result
                    cur.execute("SELECT url from " + (re.sub('[-.]', '_', job)) +
                                " WHERE build_number=?", (build,))
                    url = cur.fetchall()
                    failed_jobs[job]['url'] = url

    db_con.close()
    return failed_jobs


def get_db_builds_number(db_con, jobs):
    builds = {}
    for job in jobs:
        cur = db_con.cursor()
        cur.execute("SELECT build_number from " + (re.sub('[-.]', '_', job)))
        select = cur.fetchall()
        db_con.close()
        builds[job] = select
    return builds


def open_db_conn(db):
    con = sqlite3.connect(db)
    con.row_factory = lambda cursor, row: row[0]
    return con


def update_db(db_con, instance, jobs, builds_in_db=None, init=False):
    for job in jobs:
        if init:
            result = \
                instance[job]['lastCompletedBuild']['result']
            url = instance[job]['lastCompletedBuild']['url']
            number = instance[job]['lastCompletedBuild']['number']
            cur = db_con.cursor()
            cur.execute("INSERT INTO " + (re.sub('[-.]', '_', job)) +
                        " (build_number , result, url) "
                        "VALUES (?, ?, ?)", (
                            number, result, url))
            db_con.commit()
        else:
            for i in range(len(instance[job]['builds'])):
                url = instance[job]['builds'][i]['url']
                result = instance[job]['builds'][i]['result']
                number = instance[job]['builds'][i]['number']
                if number not in builds_in_db[job]:
                    cur = db_con.cursor()
                    cur.execute("INSERT INTO " + (re.sub('[-.]', '_', job)) +
                                " (build_number , result, url) "
                                "VALUES (?, ?, ?)", (
                                    number, result, url))
                    cur.execute()
                    db_con.close()
