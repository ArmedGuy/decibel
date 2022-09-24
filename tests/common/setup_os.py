from decibel import Runbook
from decibel.ansible.tasks import define
from decibel.flow import after, before, run, tags
from decibel.dsl import wants, default
from decibel.tasks import get_file

from tests.common.roles.service_agents import ConsulAgent, VaultAgent, ConsulTemplate
from tests.common.roles.megacli import Megacli

(
    set_fact,
    action,
    meta,
    tempfile,
    openssh_keypair,
    command,
    copy,
    user,
    file
) = define(
    "set_fact", "action", "meta", "tempfile", "openssh_keypair", "command",
    "copy", "user", "file"
)

@run
def setup_user():
    set_fact(
        ansible_user="ubuntu"
    )
    ping = action("ping").with_settings(
        ignore_errors=True,
        ignore_unreachable=True
    )
    meta("clear_host_errors")
    set_fact(
        ansible_user="siteops"
    ).when(ping.failed() | ping.unreachable() | default(False))

class SetupOS(Runbook):
    def setup(self):
        setup_user()

    @after(setup_user)
    def run_setup_backup_key(self):
        tmp = tempfile(
            state="file"
        )
        key = openssh_keypair(
            path="{{ keyfile.path }}",
            size=4096
        ).where(keyfile=tmp)
        set_fact(
            backup_pubkey="{{ backup_pubkey }}"
        ).where(backup_pubkey=key)

        command("mv {{ keyfile.path }} /root/.ssh.backup_id_rsa")
        copy(
            dest="/root/.ssh/backup_id_rsa.pub",
            content="{{ backup_pubkey.public_key }}"
        ).where(
            backup_pubkey=key
        )

    @after("run_setup_backup_key")
    def run_setup_backup_dir(self):
        user(
            name="tier-{{ tier }}",
            generate_ssh_key=True
        ).on_all("{{ groups.seedvault_nodes }}")

    @after(setup_user)
    @after("run_setup_backup_key")
    def run_setup_agents(self):
        ConsulAgent(
            datacenter=self.vars.datacenter
        )
        VaultAgent(
            datacenter=self.vars.datacenter
        )
        ConsulTemplate(
            datacenter=self.vars.datacenter
        )
    

    @before("run_setup_agents")
    @after(setup_user)
    def run_setup_siteops(self):
        file(
            path="/localhome",
            state="directory"
        )
        usr = user(
            name="siteops",
            comment="Site Operations",
            home="/localhome/siteops",
            shell="/bin/bash",
            groups="sudo",
            append=True
        )
        copy(
            remote_src=True,
            src="/home/ubuntu.ssh",
            dest="/localhome/siteops",
            owner="siteops",
            group="siteops"
        ).when(usr.changed())
        get_file(
            src="files/siteops_sudoers",
            dest="/etc/sudoers.d/siteops",
            validate="visudo -cf %s",
            mode="0440"
        )

    @tags("swag", "yolo")
    @after(VaultAgent.run_do, ConsulAgent.run_do)
    def run_the_yolo_swag_setup(self):
        get_file(
            src="files/siteops_sudoers",
            dest="/etc/sudoers.d/siteops",
            validate="visudo -cf %s",
            mode="0440"
        ).run_once().on("{{ groups.trafficlb_nodes }}")

        wants(
            command("test /tmp/yolo").ok,
            command("ls -la /").is_success,
        ).by(
            command("do_magic_stuff")
        )

        Megacli()

