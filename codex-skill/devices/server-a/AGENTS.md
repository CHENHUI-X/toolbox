# User preferences

- All machine-learning jobs created for this user, including training, evaluation, and inference, must use the user's requested 极度高优 priority. For Luban production jobs, explicitly submit with `--priority high` and verify the returned backend priority (currently `1`). Do not rely on the default priority.
- Do not submit low-priority/development jobs to save resources or shorten queues. Luban `--dev` ignores `--priority high`; choose production resources that support high priority instead. Preserve ongoing work and avoid restarting healthy training just to change evaluation resources.
- When reporting progress, verify both current platform state and current-instance logs. Preemption/recreation can leave old progress logs on shared storage; do not describe those as live progress.
