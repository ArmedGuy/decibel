from decibel import Runbook
from decibel.ansible.tasks import define

(
    apt,
    command
) = define(
    "ansible.builtin.apt",
    "ansible.builtin.command"
)

class ConsulAgent(Runbook):
    def run_do(self):
        apt(
            name="consul",
            state="installed"
        )
        command(f"consul --datacenter={self.vars.datacenter}")

class VaultAgent(Runbook):
    def run_do(self):
        apt(
            name="vault",
            state="installed"
        )

class ConsulTemplate(Runbook):
    def run_do(self):
        apt(
            name="consul-template",
            state="installed"
        )