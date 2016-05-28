# jenkins-jobs-analyzer
1)Parse results of jenkins jobs execution for jobs described in jobs.yaml
2)If init_run - store last_builds in db
3)if not init_run check for skipped builds from last reporters run and write them to db
4)check for failed jobs in db, if init run - check last successfull build, if not init run - check for skipped builds and check for failures in builds results 
