# stupid
a CLI client for certain features of stud.ip
## Install
### bundled ("binaries")
With every release, we offer a bundled version of stupid for Windows, macOS and Linux. You can download the executables for your device here: [https://github.com/LennikGamez/stupid/releases/latest](https://github.com/LennikGamez/stupid/releases/latest).

### Linux packages
The common way to install an application on Linux is by using a package manager.

We provide packages for Debian- and Red Hat-based distributions, as well as Arch Linux, on our Forgejo instance: [https://git.aws1313.de/aws1313/stupid/packages](https://git.aws1313.de/aws1313/stupid/packages).

Simply select the package for your packaging system and follow the instructions provided.
## Feature Roadmap
- [ ] authentication with direct login 
- [ ] get current courses, sync announcements and make them available via RSS
- [ ] sync files per course in specific directory structure
- [ ] system to track homework (with due date, participants, ...)
- [ ] containerized version for usage with nextcloud, syncthing or webserver

## DEVELOPEMENT INFO
- for developing set `DEBUG=True` in your environment - for example with `export DEBUG=True`
- to be able to prepare migrations, stupid has to be run at least once. prepare them with `alembic revision --autogenerate -m "MIGRATION NAME"`
- when stupid starts, an automatic database migration is run
- API: [https://docs.gitlab.studip.de/entwicklung/jsonapi/start/](https://docs.gitlab.studip.de/entwicklung/jsonapi/start/)

## DISCLAIMER
This project is not affiliated with stud.ip.

Use at your own risk.

This project is not vibe coded.
