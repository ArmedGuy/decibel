from decibel import Runbook
from decibel.tasks import get_file
from decibel.ansible.tasks import copy, apt, file

class Megacli(Runbook):
    def run_do(self):
        get_file(
            src="files/megacli.deb",
            dest="/tmp/megacli.deb"
        )
        apt(
            deb="/tmp/megacli.deb"
        )
        file(
            src="/opt/MegaRAID/MegaCLI/MegaCli64",
            dest="/usr/sbin/megacli",
            state="link"
        )
