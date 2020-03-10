#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script that uses the python stdlib to install necessary cluster dependencies.

Installs:
    Master:
        - Docker
        - S3FS
        - GLAuth (LDAP)
        - Java
        - Cromwell
    Compute:
        - ldap-client
        - Docker

Takes in 5 position arguments: {cromwell_db_user} {cromwell_db_password} {S3_Key} {S3_Secret} {bucket_name}
"""

import os
import sys
import shutil
import subprocess
import socket 
import shutil
import urllib2
import json
import StringIO

if sys.version_info[0] == 2:
    import ConfigParser as configparser
else:
    import configparser


def install_utils():
    rc = subprocess.check_call(["yum", "install", "-y", "java-1.8.0", "fuse-utils", "openssl", "wget", "zsh", "rbash"])
    if rc != 0:
        print("Failed at installing java and fuse-utils.")
        sys.exit(1)

    return 0

def add_users():
    rc = subprocess.check_call("sudo useradd cromwell", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at adding cromwell user.")
        sys.exit(1)

    return 0

# Generates self-signed ssl certifcate for glauth which handles user and group management.
def generate_ldap_ssl_cert():

    os.makedirs("/efs/certs")
    os.makedirs("/opt/glauth")

    rc = subprocess.check_call(" ".join(["sudo", "openssl", "req", "-new", "-x509", 
                    "-nodes", "-keyout", "ldap.key", "-out", "ldap.crt",
                    "-days", "3600", "-subj", "/C=US/ST=NY/L=MSSM/O=MSSM/OU=IIDSGT/CN=$(hostname)"]),
                    shell=True)
    if rc != 0:
        print("Failed at creating openssl.")
        sys.exit(1)
    
    shutil.copy2("./ldap.key", "/opt/glauth")
    shutil.copy2("./ldap.crt", "/efs/certs")

    rc = subprocess.check_call(["sudo", "echo", "tls_reqcert", "allow", ">>", "/etc/nslcd.conf"])
    if rc != 0:
        print("Failed at adding tls req to nslcd config.")
        sys.exit(1)

    return 0

# Download glauth, install and setup ldap service.
def install_glauth():
    env = os.environ.copy()
    try:
        os.makedirs("/opt/glauth")
    except:
        pass

    try:
        os.makedirs("/efs/opt")
    except:
        pass

    contents = urllib2.urlopen("https://api.github.com/repos/glauth/glauth/releases/latest").read()
    glauth_release = json.loads(contents)['assets'][10]
    glauth_url = glauth_release['browser_download_url']
    glauth_name = glauth_release['name']

    rc = subprocess.check_call("cd /opt/glauth && wget %s \
                                && chmod +x /opt/glauth/%s" % (glauth_url, glauth_name), 
                                shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at downloading glauth.")
        sys.exit(1)
    try:
        host_name = socket.gethostname() 
        host_ip = socket.gethostbyname(host_name)
    except:
        print("Failed to get hostname.")
        sys.exit(1)

    rc = subprocess.check_call("cd /opt/glauth && wget \
                                https://gitlab.com/iidsgt/parallel-cluster/-/raw/master/glauth.cfg", 
                                shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed to download glauth config file.")
        sys.exit(1)

    service_file = """
[Unit]
Description=Glauth

[Service]
Type=simple
WorkingDirectory=/opt/glauth/
ExecStart=/opt/glauth/{} -c /opt/glauth/glauth.cfg
Restart=on-failure

[Install]
WantedBy=multi-user.target
""".format(glauth_name)

    with open("/etc/systemd/system/glauth.service", "w") as fp:
        fp.write(service_file)

    with open("/efs/opt/hostname", "w") as fp:
        fp.write(host_name)

    rc = subprocess.check_call("sudo systemctl enable glauth", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at enabling glauth daemon.")
        sys.exit(1)

    rc = subprocess.check_call("sudo systemctl start glauth", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at starting glauth daemon.")
        sys.exit(1)

    rc = subprocess.check_call("cd /opt/ && wget https://gitlab.com/iidsgt/parallel-cluster/-/raw/master/ldap_authenticator.py \
                                && chmod +x ldap_authenticator.py", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at downloading ldap authenticator.")
        sys.exit(1)

    with open("/opt/ltpsecret", "w") as fp:
        fp.write("55ew7o9fhdakjvnpds98rt857tbb")

    rc = subprocess.check_call('echo "AuthorizedKeysCommand /opt/ldap_authenticator.py" >> /etc/ssh/sshd_config',
                                shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at adding config line to SSHD")
        sys.exit(1)

    
    rc = subprocess.check_call('echo "AuthorizedKeysCommandUser ec2-user" >> /etc/ssh/sshd_config',
                                shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at adding authorized user line to SSHD")
        sys.exit(1)

    rc = subprocess.check_call("sudo systemctl restart sshd", shell=True, executable="/bin/bash")
    if rc != 0:
        print(subprocess.check_output("sudo systemctl status sshd", shell=True, executable="/bin/bash"))
        print("Failed at restarting sshd")
        sys.exit(1)

    return 0

# Install ldap client and bind into the directory.
def install_ldap_client():
    rc = subprocess.check_call("yum install -y openldap-clients pam_ldap nss-pam-ldapd authconfig", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at installing ldap client.")
        sys.exit(1)

    rc = subprocess.check_call("""authconfig --enableldapauth --ldapserver=ldaps://$(cat /efs/opt/hostname):389 --ldapbasedn=dc=pcprod,dc=com --enablemkhomedir --update""", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at setting ldap client.")
        sys.exit(1)

    return 0

# Install and start docker service.
def install_docker():
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

# Install s3fs on the master node.
def install_goofys(s3_key, s3_secret, bucket_name):
    os.makedirs("/s3/%s" % (bucket_name))
    os.makedirs("/root/.aws")

    rc = subprocess.check_call("cd /usr/bin/ && sudo wget https://github.com/kahing/goofys/releases/latest/download/goofys", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at installing Goofys")
        sys.exit(1)

#     credentials = """
# [default]
# aws_access_key_id = {}
# aws_secret_access_key = {}
# """.format(s3_key, s3_secret)

#     with open("/root/.aws/credentials", "w") as fp:
#         fp.write(credentials)

    rc = subprocess.check_call("echo 'goofys#%s   /s3/%s       fuse     _netdev,allow_other,--file-mode=0666,--dir-mode=0777    0       0' \
                    >> /etc/fstab" % (bucket_name, bucket_name), shell=True, executable="/bin/bash")

    if rc != 0:
        print("Failed at adding fstab entry for goofys.")
        sys.exit(1)

    return 0


# Download and install cromwell, setup service and enable cromwell.
def install_cromwell(cromwell_user, cromwell_password):
    os.makedirs("/opt/cromwell")
    
    rc = os.system("chmod 755 /opt/cromwell")
    if rc != 0:
        print("Failed at changing cromwell directory ownership.")
        sys.exit(1)

    contents = urllib2.urlopen("https://api.github.com/repos/broadinstitute/cromwell/releases/latest").read()
    cromwell_release = json.loads(contents)['assets'][0]
    cromwell_url = cromwell_release['browser_download_url']
    cromwell_name = cromwell_release['name']

    rc = subprocess.check_call("cd /opt/cromwell && wget %s" % (cromwell_url), shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at downloading cromwell.")
        sys.exit(1)

    cromwell_script = """
#!/bin/bash
java -Dconfig.file=/opt/cromwell/cromwell.conf -jar /opt/cromwell/{} server >> /tmp/cromwell.log
""".format(cromwell_name)

    with open("/opt/cromwell/run_cromwell_server.sh", "w") as fp:
        fp.write(cromwell_script)

# Install the cromwell config file in /opt/cromwell

    cromwell_config = urllib2.urlopen("https://gitlab.com/iidsgt/parallel-cluster/-/raw/master/cromwell.conf").read()

# Change the database user and password in config file.

    cromwell_config = cromwell_config.replace("dummyuser", cromwell_user)
    cromwell_config = cromwell_config.replace("dummypassword", cromwell_password)

    with open("/opt/cromwell/cromwell.conf", "w") as fp:
        fp.write(cromwell_config)

    rc = subprocess.check_call("chmod +x /opt/cromwell/run_cromwell_server.sh", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at making cromwell script executable.")
        sys.exit(1)

# Writes the systemd config file for cromwell

    service_file = """
[Unit]
Description=Starts the Cromwell server

[Service]
Type=simple
User=cromwell
ExecStart=/opt/cromwell/run_cromwell_server.sh

[Install]
WantedBy=multi-user.target
"""

    with open("/etc/systemd/system/cromwell.service", "w") as fp:
        fp.write(service_file)

    rc = subprocess.check_call("sudo systemctl enable cromwell", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at enabling cromwell.")
        sys.exit(1)


    rc = subprocess.check_call("sudo systemctl start cromwell", shell=True, executable="/bin/bash")
    if rc != 0:
        print("Failed at starting cromwell.")
        sys.exit(1)

    return 0


def main():
    #instanceid = urllib2.urlopen('http://169.254.169.254/latest/meta-data/instance-id').read()
    # instance_type = subprocess.check_output("aws ec2 describe-instances \
    #                         --instance-id %s \
    #                         --query 'Reservations[].Instances[].Tags[?Key==`Name`].Value[]' \
    #                         --output text", 
    #                         shell=True)
    
    # This file defines all the env variables that parallel cluster uses.
    # Reading this in allows us to determin what type of node this is by 
    # looking at cfn_node_type

    cromwell_user = sys.argv[1]
    cromwell_password = sys.argv[2]
    s3_key = sys.argv[3]
    s3_secret = sys.argv[4]
    bucket_name = sys.argv[5]

    with open("/etc/parallelcluster/cfnconfig") as fp:
        for line in fp.readlines():
            l = line.rstrip().split("=")
            if l[0] == "cfn_node_type":
                instance_type = l[1]
                break

    if instance_type == "MasterServer":
        install_utils()
        add_users()
        install_docker()
        generate_ldap_ssl_cert()
        install_goofys(s3_key, s3_secret, bucket_name)
        install_glauth()
        install_ldap_client()
        install_cromwell(cromwell_user, cromwell_password)

    else:
        install_docker()
        install_ldap_client()

if __name__ == "__main__":
    main()