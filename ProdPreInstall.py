#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import subprocess
import sys

def install_docker():
    try:
        os.makedirs("/efs/opt/docker")
    except:
        pass

    rc = subprocess.check_call("sudo amazon-linux-extras install -y docker", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at installing docker.")
        sys.exit(1)
    rc = subprocess.check_call("sudo systemctl enable docker", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at enabling docker daemon.")
        sys.exit(1)

    rc = subprocess.check_call("sudo systemctl start docker", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at starting docker daemon.")
        sys.exit(1)

    return 0

def main():
    install_docker()

if __name__ == "__main__":
    main()