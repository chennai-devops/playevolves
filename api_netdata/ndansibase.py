from  jinja2 import FileSystemLoader, Environment
from tempfile import NamedTemporaryFile
from collections import namedtuple

from ansible.parsing.dataloader import DataLoader
from ansible.inventory import Inventory
from ansible.vars import VariableManager
from ansible.executor import playbook_executor
from ansible.utils.display import Display

#Setup the hosts file
def ansi_runner(server_name, server_ip, play, verbosity=0, connection='ssh', become=False, become_method='sudo', become_user='root'):
    tf = NamedTemporaryFile(prefix="ansihosts_")
    env = Environment(loader=FileSystemLoader(["."]))
    template = env.get_template("host.ini.j2")

    if play == 'nginx':
        stream = template.stream(server_name="localhost", server_ip="127.0.0.1", connection=connection)
    else:
        stream = template.stream(server_name=server_name, server_ip=server_ip, connection=connection)
    for s in stream:
        tf.file.write(s)

    tf.file.flush()

    Options = namedtuple('Options',['connection', 'module_path', 'forks', 'become',
                         'become_method', 'become_user', 'check', 'listhosts', 
                         'listtasks', 'listtags', 'syntax', 'verbosity'])

    extra_vars = {'server_name': server_name, 'server_ip': server_ip}
    loader = DataLoader()
    variable_manager = VariableManager()
    variable_manager.extra_vars = extra_vars

    options = Options(connection=connection, module_path="", forks=100, become=become,
                        become_method="sudo", become_user="root", check=False,
                        listhosts=False, listtasks=False, listtags=False, syntax=None,
                        verbosity=verbosity)
    passwords = dict(vault_pass='secret')

    inventory = Inventory(loader=loader, variable_manager=variable_manager,
                          host_list=tf.name)
    variable_manager.set_inventory(inventory)
    display = Display()
    display.verbosity = verbosity

    playbook_executor.verbosity = verbosity

    playbooks = ['./{0}/site.yml'.format(play)]

    executor = playbook_executor.PlaybookExecutor(
                playbooks=playbooks,
                inventory=inventory,
                loader=loader,
                variable_manager=variable_manager,
                options=options,
                passwords=passwords
                )

    executor.run()
    stats = executor._tqm._stats

    run_success = True
    hosts = sorted(stats.processed.keys())

    for h in hosts:
        t = stats.summarize(h)
        if t['unreachable'] > 0 or t['failures'] > 0:
            run_success = False

    return run_success


