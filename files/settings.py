import os

JENKINS_JOBS_YAML = os.getenv('JENKINS_JOBS_YAML')
JENKINS_HOST = os.getenv('JENKINS_HOST')
sender = os.getenv('SENDER')
receiver = os.getenv('RECEIVER')
password = os.getenv('PASSWORD')
smtp_server = os.getenv('SMTP')
database = os.getenv('DATABASE')
init_run = os.getenv('REPORTER_INIT_RUN', False)
