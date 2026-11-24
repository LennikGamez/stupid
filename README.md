# stupid
a CLI client for certain features of stud.ip
## Install
### bundled ("binaries")
With every release, we offer a bundled version of stupid for Windows, Linux and macOS (not recommended). You can download the executables for your device here: [https://github.com/LennikGamez/stupid/releases/latest](https://github.com/LennikGamez/stupid/releases/latest).

### Linux packages
The common way to install an application on Linux is by using a package manager.

We provide packages for Debian- and Red Hat-based distributions, as well as Arch Linux, on our Forgejo instance: [https://git.aws1313.de/aws1313/stupid/packages](https://git.aws1313.de/aws1313/stupid/packages).

Simply select the package for your packaging system and follow the instructions provided.

### MacOS
Distributing for macOS can be a little bit complicated if you are not willing to pay 100€ a year. 

We decided to go with a `homebrew tap`, which is kind of a third-party repository for homebrew.

You can install stupid by running `brew install aws1313/tap/stupid`.

The corresponding repository can be found here: [https://github.com/aws1313/homebrew-tap](https://github.com/aws1313/homebrew-tap)

> [!Note]
> Stupid uses the system keychain to store your password safely, please grant permission when asked.

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
