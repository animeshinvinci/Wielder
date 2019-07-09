#!/usr/bin/env python
import os

from wielder.util.util import get_kube_context
from wielder.wield.enumerator import WieldAction
from wielder.wield.modality import WieldMode, WieldServiceMode

__author__ = 'Gideon Bar'

import argparse

import yaml

from collections import namedtuple

from wielder.util.commander import async_cmd

CONTEXT_MINI = 'minikube'
CONTEXT_DOCKER = 'docker-for-desktop'

LOCAL_CONTEXTS = [CONTEXT_DOCKER, CONTEXT_MINI]


class Conf:

    def __init__(self):

        self.template_ignore_dirs = []

    def attr_list(self, should_print=False):

        items = self.__dict__.items()
        if should_print:

            print("Conf items:\n______\n")
            [print(f"attribute: {k}    value: {v}") for k, v in items]

        return items


def destroy_sanity(conf):

    if conf.deploy_env is 'prod':

        print('You are trying to destroy a production environment!!!'
              'Exiting!!!')

        exit(1)

    # TODO enable this
    # elif conf.deploy_env is not 'local' or conf.kube_context is not "minikube":
    #
    #     confirm_destroy = input('Enter Y if you wish to destroy')
    #
    #     if confirm_destroy is not 'Y':
    #
    #         print('Exiting')
    #
    #         exit(1)


def replace_none_vars_from_args(action, mode, local_mount, enable_debug, service_mode, project_override):

    kube_parser = get_kube_parser()
    kube_args = kube_parser.parse_args()

    if not mode:

        mode = WieldMode(
            runtime_env=kube_args.runtime_env,
            deploy_env=kube_args.deploy_env
        )

    if not action:
        action = kube_args.wield

    if not enable_debug:
        enable_debug = kube_args.enable_debug

    if not local_mount:
        local_mount = kube_args.local_mount

    if not service_mode:

        service_mode = WieldServiceMode(
            debug_mode=enable_debug,
            local_mount=local_mount,
            project_override=project_override
        )

    return action, mode, enable_debug, local_mount, service_mode


def get_kube_parser():

    parser = argparse.ArgumentParser(
        description='Three rings for the cloud-kings in the sky,\n'
                    'Seven for the CI-CD-lords in their halls of stone,\n'
                    'Nine for mortal services doomed to die,\n'
                    'One for the Wielder on his Python throne\n'
                    'In the Land of Babylon where technologies lie.\n'
                    'One ring to rule them all, One ring to find them,\n'
                    'One ring to bring them all, and in the a framework bind them,\n'
                    'In the Land of Babylon where technologies lie.\n\n'
                    
                    'Created by Gideon Bar to tame Bash, Git, Terraform, Containers, Kubernetes, Cloud CLIs etc.\n'
                    'In to one debugable understandable Python framework.'
    )

    parser.add_argument(
        '-w', '--wield',
        type=WieldAction,
        choices=list(WieldAction),
        help='Wield actions:\n'
             'plan: produces the configuration without applying it e.g. yaml for kubernetes or terraform vars\n'
             'apply: deploys the plan\n'
             'delete: deletes the deployed resources',
        default=WieldAction.PLAN
    )

    parser.add_argument(
        '-cf', '--conf_file',
        type=str,
        help='Full path to config file with all arguments.\nCommandline args override those in the file.'
    )

    parser.add_argument(
        '-kc', '--kube_context',
        type=str,
        help='Kubernetes context i.e. run locally on docker or in cloud e.g.'
             '\ndocker-for-desktop'
    )

    parser.add_argument(
        '-re', '--runtime_env',
        type=str,
        choices=['docker', 'gcp', 'on-prem', 'aws', 'azure'],
        help='Runtime environment refers to where the Kubernetes cluster is running',
        default=None
    )

    parser.add_argument(
        '-de', '--deploy_env',
        type=str,
        choices=['local', 'dev', 'int', 'qa', 'stage', 'prod'],
        help='Deployment environment refers to stages of production',
        default=None
    )

    parser.add_argument(
        '-cpr', '--cloud_provider',
        type=str,
        choices=['gcp', 'aws', 'azure'],
        help='Cloud provider will only mean something if not local:'
    )

    parser.add_argument(
        '-gp', '--gcp_project',
        type=str,
        choices=['marketo-webpersonalization-dev', 'rtp-gcp-poc'],
        help='GCP project for GKE means:\n'
             'Which project to use for deploy and resources.'
    )

    parser.add_argument(
        '-edb', '--enable_debug',
        type=bool,
        default=False,
        help='Enabling Debug ports for remote debugging:'
    )

    parser.add_argument(
        '-edv', '--enable_dev',
        type=bool,
        help='Enabling Development on pods e.g. running a dud while loop instead of the server process:'
    )

    parser.add_argument(
        '-lm', '--local_mount',
        type=bool,
        default=False,
        help='If kubernetes should mount a local directory to the docker, used for local development'
    )

    parser.add_argument(
        '-ds', '--deploy_strategy',
        type=str,
        help='Deployment strategy e.g. "lean" means:\n'
             'single mongo and redis pods to conserve resources while developing or testing'
    )

    return parser


def wielder_sanity(conf, mode, service_mode=None):

    context = get_kube_context()

    if conf.kube_context != context:

        print(f"There is a discrepancy between the configured and actual contexts:"
              f"\nkube context   : {conf.kube_context}"
              f"\ncurrent context: {context} "
              f"\neither add context in command-line args or in config file or"
              f"\nto change context run:"
              f"\nkubectl config use-context <the context you meant>"
              f"\n!!! Exiting ...")
        exit(1)
    else:
        print(f"kubernetes current context: {context}")

    message = f"There is a discrepancy between context and runtime environment:" \
        f"\nkube context   : {conf.kube_context}" \
        f"\nmode.runtime_env is: {mode.runtime_env}" \
        f"\neither change context or configure congruent runtime_env" \
        f"\nto change context run:" \
        f"\nkubectl config use-context <the context you meant>" \
        f"\n!!! Exiting ..."

    if context == 'docker-for-desktop' and mode.runtime_env != 'docker':
        print(message)
        exit(1)
    elif 'gke' in context and mode.runtime_env != 'gcp':
        print(message)
        exit(1)

    if not service_mode:
        return

    if context != 'docker-for-desktop' and service_mode.local_mount:

        print(f"Local mount of code into container is only allowed on local development env:"
              f"\nkube context   : {conf.kube_context}"
              f"\nmode.local_mount is: {service_mode.local_mount} "
              f"\neither change context or flag local_mount as false"
              f"\nto change context run:"
              f"\nkubectl config use-context <the context you meant>"
              f"\n!!! Exiting ...")
        exit(1)


def sanity(conf):

    context = async_cmd('kubectl config current-context')[0][:-1]

    if conf.kube_context != context:

        print(f"There is a discrepancy between the configured and actual contexts:"
              f"\nkube context   : {conf.kube_context}"
              f"\ncurrent context: {context} "
              f"\neither add context in command-line args or in config file or"
              f"\nto change context run:"
              f"\nkubectl config use-context <the context you meant>"
              f"\n!!! Exiting ...")
        exit(1)
    else:
        print(f"kubernetes current context: {context}")

    if conf.deploy_env == 'local':

        if conf.kube_context not in LOCAL_CONTEXTS:

            print(f"There is a discrepancy between deploy_env: {conf.deploy_env} "
                  f"and kube_context: {conf.kube_context}.\n"
                  f"If you meant to one of these:\n{LOCAL_CONTEXTS} run:\n"
                  f"kubectl config use-context <some local-context>\n"
                  f"!!! Exiting ...")
            exit(1)

    print(f"conf.supported_deploy_envs: {conf.supported_deploy_envs}")

    if conf.deploy_env not in conf.supported_deploy_envs:

        print(f"We do not support deploy_env: {conf.deploy_env}!!!\n"
              f"If you want to support it add it in:\n"
              f"conf file in supported_deploy_envs field\n"
              f"!!! Exiting ...")
        exit(1)

    # TODO add sanity for debug flag
    # TODO check if configured images exist in repository using docker images | grep or gcloud ...


def process_args(cmd_args, perform_sanity=True):

    if cmd_args.conf_file is None:

        dir_path = os.path.dirname(os.path.realpath(__file__))

        cmd_args.conf_file = dir_path + '/wielder_conf.yaml'

    with open(cmd_args.conf_file, 'r') as yaml_file:
        conf_args = yaml.load(yaml_file, Loader=yaml.UnsafeLoader)

    if not hasattr(conf_args, 'plan'):
        conf_args['plan'] = False

    print('Configuration File Arguments:')

    config_items = cmd_args.__dict__.items()

    for k, v in config_items:

        if v is not None:
            conf_args[k] = v

    named_tuple = namedtuple("Conf1", conf_args.keys())(*conf_args.values())

    conf = Conf()

    conf.plan = named_tuple.plan
    conf.conf_file = named_tuple.conf_file
    conf.deploy_env = named_tuple.deploy_env
    conf.enable_debug = named_tuple.enable_debug
    conf.enable_dev = named_tuple.enable_dev
    conf.deploy_strategy = named_tuple.deploy_strategy
    conf.supported_deploy_envs = named_tuple.supported_deploy_envs
    conf.kube_context = named_tuple.kube_context
    conf.cloud_provider = named_tuple.cloud_provider
    conf.gcp_image_repo_zone = named_tuple.gcp_image_repo_zone
    conf.gcp_project = named_tuple.gcp_project
    conf.template_ignore_dirs = named_tuple.template_ignore_dirs
    conf.template_variables = named_tuple.template_variables
    conf.script_variables = named_tuple.script_variables

    conf.raw_config_args = conf_args

    if perform_sanity:
        sanity(conf)

    conf.attr_list(True)

    return conf


if __name__ == "__main__":

    _kube_parser = get_kube_parser()
    _kube_args = _kube_parser.parse_args()

    _conf = process_args(_kube_args)

    destroy_sanity(_conf)



