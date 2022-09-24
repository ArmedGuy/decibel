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
    def run_configure(self):
        template(
            src="files/haproxy.cfg.j2",
            dest="/etc/haproxy/haproxy.cfg"
        )
        if self.vars.datacenter.value() == "dc1":
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
from decibel.ansible import command, stat
from decibel.dsl import gets

class Database(Runbook):
    def run_import(self):
        gets(
            stat(path="/tmp/mysql-import.log").stat.exists,
            command("mysql -e 'SELECT * FROM db'").ok
        ).via(
            command("mysql-import file.sql")
        )
```

### Why is it called Decibel?
Well, see, I tried to name it DSLible, because the goal was to create a more DSL-like language to use for Ansible. But DSLible is very hard to say, and the most important thing about project names is how easy you can fit it into a workplace discussion. Decibel sounded close enough, and also happens to lay the ground for a really cheeky slogan.