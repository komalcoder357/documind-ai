def stage(db, job, name, done, total):
    job.stage, job.steps_done, job.steps_total = name, done, total; db.commit()
