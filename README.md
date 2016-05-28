# jenkins-jobs-analyzer tools

# check for failed jobs
#1.1)Parse results of jenkins jobs execution for jobs described in jobs.yaml

#1.2)If init_run - create db and store jenkins_jobs_last_builds info in db

#1.3)if not init_run check for skipped runs in db, retrieve skipped info and write them to db

#1.4)check for failed jobs in db, if init run - check last successful build, if not init run - check for  for failures in db_builds results

#1.5) send details of failed jobs via email
