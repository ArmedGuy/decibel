from decibel import Runbook
from decibel.ansible.tasks import define
from decibel.tasks import get_file

(apt, ) = define("apt")

class SetupOS(Runbook):
    def run_test(self):
        get_file(
            src="file1.txt",
            dest="/etc/file1.txt"
        )