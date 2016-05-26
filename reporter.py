import jenkins
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import yaml
import os
import sqlite3
import re
import pprint


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


def get_jobs_last_build_number(job_instances, jobs):
    jobs_last_builds = {}
    for job_name in jobs:
        jobs_last_builds[job_name] = \
            job_instances[job_name]['lastCompletedBuild']['number']
    return jobs_last_builds


def send_mail(list_of_failed_jobs, sender, reciever, password, smtp_server):
    fromaddr = sender
    toaddr = reciever
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "gating"
    body = "list of failed jobs \n {}".format(pprint.pformat(list_of_failed_jobs))
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(smtp_server, 587)
    server.starttls()
    server.login(fromaddr, password)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()


def create_database(db, jobs):
    con = sqlite3.connect(db)
    cur = con.cursor()
    for job in jobs:
        job = re.sub('[-.]', '_', job)
        table_exist = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (job,))
        if not table_exist.fetchone():
            cur.execute("CREATE TABLE  " + job +
                        " (build_number INT, "
                        "result VARCHAR(30),"
                        "url VARCHAR(30))")
    con.commit()
    con.close()


def write_job_results_to_db(jobs_instance, jobs, db, jobs_last_numbers):
    #  check record in db for build, if exist - skip
    for job in jobs:
        con = sqlite3.connect(db)
        con.row_factory = lambda cursor, row: row[0]
        cur = con.cursor()
        cur.execute("SELECT build_number from " + (re.sub('[-.]', '_', job)))
        select = cur.fetchall()
        con.close()
        if jobs_last_numbers[job] not in select:
            job_result = \
                jobs_instance[job]['lastCompletedBuild']['result']
            job_url = jobs_instance[job]['lastCompletedBuild']['url']
            con = sqlite3.connect(db)
            cur = con.cursor()
            cur.execute("INSERT INTO " + (re.sub('[-.]', '_', job)) +
                        " (build_number , result, url) "
                        "VALUES (?, ?, ?)", (jobs_last_numbers[job], job_result, job_url))
            con.commit()


def check_last_build_result(jobs, jobs_build_numbers, db):
    con = sqlite3.connect(db)
    con.row_factory = lambda cursor, row: row[0]
    cur = con.cursor()
    failed_jobs = {}
    for job in jobs:
        cur.execute("SELECT result from " + (re.sub('[-.]', '_', job)) +
                    " WHERE build_number=?", (jobs_build_numbers[job], ))
        result = cur.fetchall()
        if 'FAILURE' in result:
            failed_jobs[job]= {}
            failed_jobs[job]['result'] = result
            cur.execute("SELECT url from " + (re.sub('[-.]', '_', job)) +
                        " WHERE build_number=?", (jobs_build_numbers[job],))
            url = cur.fetchall()
            failed_jobs[job]['url'] = url
    return failed_jobs


if __name__ == '__main__':
    JENKINS_JOBS_YAML = os.getenv('JENKINS_JOBS_YAML')
    JENKINS_HOST = os.getenv('JENKINS_HOST')
    sender = os.getenv('SENDER')
    reciever = os.getenv('RECIEVER')
    password = os.getenv('PASSWORD')
    smtp_server = os.getenv('SMTP')
    database = os.getenv('DATABASE')

    job_from_yaml = get_jobs_from_yaml(JENKINS_JOBS_YAML)
    instances = get_job_instances(host=JENKINS_HOST, jobs=job_from_yaml)
    jobs_build_numbers = get_jobs_last_build_number(instances, job_from_yaml)
    create_database(database, job_from_yaml)
    write_job_results_to_db(instances, job_from_yaml, database, jobs_build_numbers)
    failed_jobs = check_last_build_result(job_from_yaml, jobs_build_numbers, database)
    if failed_jobs:
        send_mail(list_of_failed_jobs=failed_jobs,
                  sender=sender,
                  reciever=reciever,
                  password=password,
                  smtp_server=smtp_server)

