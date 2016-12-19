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
        }
    ]
}


@click.command()
@click.option('--file', '-f', default='/etc/prometheus/config.yml',
              help='File to write configuration to')
@click.option('--print', '-p', default=False, is_flag=True,
              help='Prints YAML config to stdout instead of writing to file')
@click.option('--cattle-url', '-u',
              default=lambda: os.environ.get('CATTLE_URL'))
@click.option('--cattle-access-key', '-a',
              default=lambda: os.environ.get('CATTLE_ACCESS_KEY'))
@click.option('--cattle-secret-key', '-s',
              default=lambda: os.environ.get('CATTLE_SECRET_KEY'))
def write(file, print, cattle_url, cattle_access_key, cattle_secret_key):
    client = cattle.Client(url=cattle_url,
                           access_key=cattle_access_key,
                           secret_key=cattle_secret_key)
    targets = []
    for host in client.list('host'):
        click.echo('Discovered {}'.format(host.hostname))
        targets.append('{}:{}'.format(host.hostname, 9100))
    # noinspection PyTypeChecker
    config['scrape_configs'].append({
        'job_name': 'HostMetrics',
        'static_configs': [{'targets': targets}]
    })
    yml = yaml.dump(config, default_flow_style=False)
    if print:
        click.echo(yml)
    else:
        with open(file, mode='w') as f:
            f.writelines(yml)
        click.echo('Config written to {}'.format(file))


if __name__ == '__main__':
    write()
