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
            'job_name': 'ContainerMetrics',
            'dns_sd_configs': [
                {
                    'names': ['cadvisor'],
                    'refresh_interval': '15s',
                    'type': 'A',
                    'port': 8080
                }
            ]
        },
        {
            'job_name': 'rancher-api',
            'dns_sd_configs': [
                {
                    'names': ['prometheus-rancher-exporter'],
                    'refresh_interval': '15s',
                    'type': 'A',
                    'port': 9010
                }
            ]
        },
        {
            'job_name': 'Prometheus',
            'static_configs': [{'targets': ['127.0.0.1:9090']}]
        },
        {
            'job_name': 'HostMetrics',
            'file_sd_configs': [{'files': ['hosts.yml']}]
        }
    ]
}


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
    for host in client.list('host'):
        for instance in host.instances():
            if 'node-exporter' in instance.name and instance.state == 'running'ss:
                click.echo("Discovered exporter on {}".format(host.hostname))
                ip = (instance.data.fields.dockerIp or
                      instance.data.fields.dockerHostIp)
                hosts.append({
                    'targets': ['{}:{}'.format(ip, 9100)],
                    'labels': {'instance': host.hostname}
                })
                break

    config_yml = yaml.dump(config, default_flow_style=False)
    hosts_yml = yaml.dump(hosts, default_flow_style=False)
    if print:
        click.echo('# config.yml')
        click.echo('---')
        click.echo(config_yml)
        click.echo('# hosts.yml')
        click.echo('---')
        click.echo(hosts_yml)
    else:
        with open(os.path.join(config_dir, 'hosts.yml'), mode='w') as f:
            f.writelines(hosts_yml)
        with open(os.path.join(config_dir, 'config.yml'), mode='w') as f:
            f.writelines(config_yml)
        click.echo('Config written to {}'.format(config_dir))


if __name__ == '__main__':
    write()
