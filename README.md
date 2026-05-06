# pi.duts

## Feature Roadmap
- [ ] authentication with direct login 
- [ ] get current courses, sync announcements and make them available via RSS
- [ ] sync files per course in specific directory structure
- [ ] system to track homework (with due date, participants, ...)
- [ ] containerized version for usage with nextcloud, syncthing or webserver

## DEVELOPEMENT INFO
- for developing set `DEBUG=True` in your environment - for example with `export DEBUG=True`
- to be able to prepare migrations, pi_duts has to be run at least once. prepare them with `alembic revision --autogenerate -m "MIGRATION NAME"`
- when pi_duts starts, an automatic database migration is run

## DISCLAIMER
This project is not affiliated with stud.ip.

Use on you own risk.

This project is not vibe coded.