import jenkins
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import yaml
import os

def job_analyser():
    JENKINS_HOST = os.getenv('JENKINS_HOST') # Jenkins Job server
    JENKINS_JOBS_YAML = os.getenv('JENKINS_JOBS_YAML') # Path to yaml with jenkins job's to analyse
    jenkins_url = 'http://' + JENKINS_HOST
    server = jenkins.Jenkins(jenkins_url)

    # retrieve jenkins job's from yaml
    with open(JENKINS_JOBS_YAML, "r") as f:
        jobs = yaml.load(f)

    job_instances = {}

    for job_name in jobs:
        job_instances[job_name] = server.get_job_info(job_name,depth=10)

    list_of_failed_jobs = []
    for job_name in jobs:
        if job_instances[job_name]['lastCompletedBuild']['result'] == 'FAILURE':
            list_of_failed_jobs.append(job_instances[job_name]['lastCompletedBuild']['url'])
    return list_of_failed_jobs

def send_mail(list_of_failed_jobs):
    fromaddr = "agrechanichenko@mirantis.com"
    toaddr = fromaddr
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "gating"

    body = "list of failed jobs {}".format(list_of_failed_jobs)
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, "jahfqwniyiszujim")
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()

if __name__ == '__main__':
    list_of_failed_jobs = job_analyser()
    send_mail(list_of_failed_jobs)



