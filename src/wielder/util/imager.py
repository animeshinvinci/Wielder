#!/usr/bin/env python
import os
from shutil import rmtree, copyfile, copytree
from wielder.util.commander import async_cmd


def replace_file(origin_path, origin_regex, destination_path, final_name):
    """
    Validates existence of origin_regex
    Removes old destination
    Copies target with final_name to destination

    :param origin_path:
    :param origin_regex: Origin file regex e.g. App*.zip (AppV1.zip, AppV2.zip ...)
    :param destination_path:
    :param final_name:
    :return:
    """

    target_file = async_cmd(f"find {origin_path} -name {origin_regex}")[0][:-1]

    print(f'Regex "{origin_regex}"" is fount in origin_path:  {target_file}')

    if target_file == '':

        print(f"couldn't find {origin_path}/{origin_regex} please run: ")
        return

    print(f"Found {target_file} in target")

    full_destination = f"{destination_path}/{final_name}"

    try:
        os.remove(full_destination)

    except Exception as e:
        print(str(e))

    copytree(target_file, full_destination)

    print(f"successfully replaced {full_destination}")


def replace_dir_contents(origin_path, origin_regex, destination_path, destination_dir_name='artifacts'):
    """
    Used to update executable code for docker image packing
    e.g. interpreted code and artifacts.
    Validates existence of directory.
    Validates existence of a file regex in the directory for sanity purposes.
    Removes old destination.
    Copies directory contents to destination under artifacts directory

    :param origin_path: path to directory containing executables to be packed into image
    :param origin_regex: Origin file regex e.g. App*.zip (AppV1.zip, AppV2.zip ...)
           to be found in path for sanity check
    :param destination_path: A destination directory
           where the content of the executable directory can be copied to
    :param destination_dir_name: the name of the destination directory defaults to: artifacts
    :return:
    """

    target_file = async_cmd(f"find {origin_path} -name {origin_regex}")[0][:-1]

    print(
        f'Search results for regex <{origin_regex}> in origin_path:  {origin_path}:\n'
        f'{target_file}'
    )

    if target_file == '':

        print(f"couldn't find {origin_path}/{origin_regex}\nPlease make sure it exists in path")
        return

    print(f"Found {target_file} in target")

    full_destination = f"{destination_path}/{destination_dir_name}"

    try:
        rmtree(full_destination)

    except Exception as e:
        print(str(e))

    copytree(origin_path, full_destination)

    print(f"successfully replaced {full_destination}")


def push_image(gcp_conf, name, group, tag):

    gcp_name = f'{gcp_conf.image_repo_zone}/{gcp_conf.project}/{group}/{name}'

    os.system(
        f'docker tag {name}:{tag} {gcp_name}:latest;'
        f'gcloud docker -- push {gcp_name}:latest;'
        f'gcloud container images list --repository={gcp_name};'
    )


def pack_image(conf, name, image_root, push=False, force=False, tag='dev'):
    """

    :param tag:
    :param conf:
    :param name:
    :param push:
    :param force: force creation of image if it doesn't exist in repo
    :param image_root:
    :return:
    """

    dockerfile_dir = f'{image_root}/{name}'

    image_name = f'{name}'

    gcp_conf = conf.providers.gcp

    _cmd = f'docker images | grep {tag} | grep {image_name};'

    image_trace = async_cmd(
        _cmd
    )

    print(f"{name} image_trace: {image_trace}")

    # Check if the list is empty
    if force or not image_trace:

        print(f"attempting to create image {name}")

        os.system(
            f'docker build -t {image_name}:{tag} {dockerfile_dir};'
            f'echo "These are the resulting images:";'
            f'docker images | grep {tag} | grep {image_name};'
        )

    if push:
        push_image(gcp_conf)




