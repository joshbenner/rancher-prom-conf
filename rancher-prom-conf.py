#!/usr/bin/env python

import os

import click
import yaml
import cattle


config = {
    'global': {
        'scrape_interval': '15s',
        'evaluation_interval': '15s',
        'external_labels': {
            'monitor': 'exporter-metrics'
        }
    },
    'scrape_configs': [
        {
            'job_name': 'Prometheus',
            'static_configs': [{'targets': ['127.0.0.1:9090']}]
        }
    ]
}

env_names = {}


def env_name(client, env_id):
    if env_id not in env_names:
        env_names[env_id] = client.by_id('account', env_id).name
    return env_names[env_id]


@click.command()
@click.option('--config-dir', default='/etc/prometheus',
              help='Directory to write configuration')
@click.option('--print', '-p', default=False, is_flag=True,
              help='Prints YAML config to stdout instead of writing to file')
@click.option('--cattle-url', '-u',
              default=lambda: os.environ.get('CATTLE_URL'))
@click.option('--cattle-access-key', '-a',
              default=lambda: os.environ.get('CATTLE_ACCESS_KEY'))
@click.option('--cattle-secret-key', '-s',
              default=lambda: os.environ.get('CATTLE_SECRET_KEY'))
def write(config_dir, print, cattle_url, cattle_access_key, cattle_secret_key):
    client = cattle.Client(url=cattle_url,
                           access_key=cattle_access_key,
                           secret_key=cattle_secret_key)
    hosts = []
    cadvisors = []
    rancher = []
    for host in client.list('host'):
        host_ip = host.data.fields.agentIpAddress
        for instance in host.instances():
            if instance.state != 'running':
                continue
            if 'node-exporter' in instance.name:
                click.echo("Discovered node exporter on {}"
                           .format(host.hostname))
                hostname = (instance.primaryIpAddress or host_ip)
                hosts.append({
                    'targets': ['{}:{}'.format(hostname, 9100)],
                    'labels': {
                        'instance': host.hostname,
                        'rancher_env': env_name(client, instance.accountId)
                    }
                })
            elif 'cadvisor' in instance.name:
                click.echo('Discovered cadvisor on {}'.format(host.hostname))
                hostname = (instance.primaryIpAddress or host_ip)
                cadvisors.append({
                    'targets': ['{}:{}'.format(hostname, 9001)],
                    'labels': {
                        'instance': host.hostname,
                        'rancher_env': env_name(client, instance.accountId)
                    }
                })
            elif 'rancher-exporter' in instance.name:
                click.echo('Discovered rancher exporter on {}'
                           .format(host.hostname))
                hostname = (instance.primaryIpAddress or host_ip)
                rancher.append({
                    'targets': ['{}:{}'.format(hostname, 9173)],
                    'labels': {
                        'instance': host.hostname,
                        'rancher_env': env_name(client, instance.accountId)
                    }
                })

    # noinspection PyTypeChecker
    config['scrape_configs'].extend([
        {
            'job_name': 'HostMetrics',
            'file_sd_configs': [
                {'files': [os.path.join(config_dir, 'hosts.yml')]}
            ]
        },
        {
            'job_name': 'rancher-api',
            'file_sd_configs': [
                {'files': [os.path.join(config_dir, 'rancher.yml')]}
            ]
        },
        {
            'job_name': 'ContainerMetrics',
            'file_sd_configs': [
                {'files': [os.path.join(config_dir, 'cadvisors.yml')]}
            ]
        }
    ])
    files = (
        ('config.yml', yaml.dump(config, default_flow_style=False)),
        ('hosts.yml', yaml.dump(hosts)),
        ('rancher.yml', yaml.dump(rancher)),
        ('cadvisors.yml', yaml.dump(cadvisors))
    )
    if print:
        for filename, yml in files:
            click.echo('# {}'.format(filename))
            click.echo('---')
            click.echo(yml)
    else:
        for filename, yml in files:
            with open(os.path.join(config_dir, filename), mode='w') as f:
                f.writelines(yml)
            click.echo('... wrote {}'.format(filename))
        click.echo('Config written to {}'.format(config_dir))


if __name__ == '__main__':
    write()
