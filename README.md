# decibel - Turn your Infrastructure up to 11!

**Are you that IT-rockstar that Sophos makes commercials [about](https://www.youtube.com/watch?v=-CnYilm5k94), but you are stuck writing long-winding and full-of-boilerplate YAML files to set up your IT environment?**

**Do you wish your Infrastructure as Code-repository actually contained code, and not some Chomsky Type-2 markup language that requires you to carefully place everything in the right order?**

### ***Fear not, hear us out what decibel has to offer!***


#### Python-based configuration with hard dependencies
Decibel uses Python for its configuration, basing it on classes and simple functions to
define how things should run. Python decorators are used for controlling the flow of configuration, eliminating the need to define things in a certain order.
```python
from decibel import Runbook
from decibel.ansible import apt, template, command
from decibel.flow import after, notify

class HAProxy(Runbook):
    def run_install(self):
        apt(
            name="haproxy",
            state="installed"
        )

    @after("run_install")
    @notify("reload_service")
    def run_configure(self):
        template(
            src="files/haproxy.cfg.j2",
            dest="/etc/haproxy/haproxy.cfg"
        )
        if self.vars.datacenter == "dc1":
            command("program --datacenter {{ datacenter }}")

    def reload_service(self):
        service(
            name="haproxy",
            state="restarted"
        )
```

Decibel resolves all dependencies between Runbooks and Runnables, and calculates the most optimal way to perform the configuration. Runbooks exist to group together certain steps of an installation, and can be used to parameterize common steps. Variables are both available to the Python-code, but are also exported to all tasks that run within a Runbook and can be used in Jinja2.

```python
from haproxy import HAProxy
from decibel import Decibel


with Decibel() as ds:
    with ds.hosts("localhost", become=True):
        HAProxy(
            datacenter="dc1",
            backends=[
                "one.example.com",
                "two.example.com"
            ]
        )
    ds.run()
```

#### Forcing idempotence on the user
Ansible strives to have configuration be idempotent, and most modules are indeed that. There are however cases where simple modules are not idempotent by default because they require the user to configure not only what command to run, but the desired state the command should bring you to.
Decibel will be default warn you of such cases, and provide helper functions to easily make your configurations desired-state based.

```python
from decibel.ansible import command, stat, 
from decibel.dsl import wants
class Database(Runbook):
    def run_import(self):
        wants(
            stat(path="/tmp/mysql-import.log").stat.exists,
            command("mysql -e 'SELECT * FROM db').ok
        ).from(
            command("mysql-import file.sql")
        )
```

#### Lots of plumbing under the hood
Decibel handles registration and firing of handlers, variable registration and variable scope, 
task tagging. It also provides a helpful syntax for many common operations such as run once, task delegation, rolling updates, and more. 

```python
from decibel.ansible import command, apt
from decibel.flow import rolling, tags
class Webserver(Runbook):

    @rolling("1%", "5%", "40%", "80%", "100%", max_failing="10%")
    @tags("web", "apache")
    def run_upgrade(self):
        command(
            "/usr/bin/disable_host {{inventory_hostname}}"
        ).run_once().on(
            "{{ groups.trafficlb_nodes }}"
        )
        apt(
            name="apache2",
            state="latest"
        )
        command(
            "/usr/bin/enable_host {{inventory_hostname}}"
        ).run_once().on(
            "{{ groups.trafficlb_nodes }}"
        )
```