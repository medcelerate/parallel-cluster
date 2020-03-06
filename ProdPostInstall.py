#!/usr/bin/env python

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

Takes in 3 position arguments: {cromwell_db_name} {cromwell_db_user} {cromwell_db_password}
"""

import os
import sys
import shutil
import urllib2
import subprocess
import socket 
import shutil


def install_utils():
    rc = os.system("yum -y install java-1.8.0")
    if rc != 0:
        print("Failed at installing java.")
        sys.exit(1)

# Generates self-signed ssl certifcate for glauth which handles user and group management.
def generate_ldap_ssl_cert():

    os.makedirs("/efs/certs")
    os.makedirs("/opt/glauth")

    script = """
sudo openssl req  -new -x509 -nodes -keyout ldap.key -out ldap.crt -days 3600 \
-subj "/C=US/ST=NY/L=MSSM/O=MSSM/OU=IIDSGT/CN=$(hostname)"
"""

    rc = os.system(script)
    if rc != 0:
        print("Failed at creating openssl.")
        sys.exit(1)
    
    shutil.copy2("./ldap.key", "/opt/glauth")
    shutil.copy2("./ldap.crt", "/efs/certs")

    


# Download glauth, install and setup ldap service.
def install_glauth():
    os.makedirs("/opt/glauth")

    contents = urllib2.urlopen("https://api.github.com/repos/glauth/glauth/releases/latest").read()
    glauth_release = json.loads(contents)['assets'][0]
    glauth_url = glauth_release['browser_download_url']
    glauth_name = glauth_release['name']

    rc = os.system("cd /opt/glauth && wget %s" % (glauth_url))
    if rc != 0:
        print("Failed at downloading glauth.")
        sys.exit(1)
    try:
        host_name = socket.gethostname() 
        host_ip = socket.gethostbyname(host_name)
    except:
        print("Failed to get hostname.")
        sys.exit(1)

    rc = os.system("cd /opt/glauth && wget %s" % ("https://gitlab.com/iidsgt/parallel-cluster/-/raw/master/glauth.cfg"))
    if rc != 0:
        print("Failed to download glauth config file.")
        sys.exit(1)

    service_file = """
[Unit]
Description=Glauth

[Service]
Type=simple
WorkingDirectory=/opt/glauth/
ExecStart=/opt/glauth/glauth -c /opt/glauth/glauth.cfg
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""

    with open("/etc/systemd/system/glauth.service", "w") as fp:
        fp.write(service_file)

    with open("/efs/opt/hostname", "w") as fp:
        fp.write(host_name)

    rc = os.system("sudo systemctl enable glauth")
    if rc != 0:
        print("Failed at enabling docker daemon.")
        sys.exit(1)
    rc = os.system("sudo systemctl start glauth")
    if rc != 0:
        print("Failed at starting docker daemon.")
        sys.exit(1)


# Install ldap client and bind into the directory.
def install_ldap_client():
    rc = os.system("yum install -y openldap-clients pam_ldap nss-pam-ldapd authconfig")
    if rc != 0:
        print("Failed at installing ldap client.")
        sys.exit(1)

    rc = os.system('authconfig --enableldap --enableldapauth --ldapserver=$(cat /efs/opt/hostname) --ldapbasedn="dc=pcprod,dc=com" --enableldaptls --update')
    if rc != 0:
        print("Failed at setting ldap client.")
        sys.exit(1)

# Install and start docker service.
def install_docker():
    rc = os.system("sudo amazon-linux-extras -y install docker")
    if rc != 0:
        print("Failed at installing docker.")
        sys.exit(1)
    rc = os.system("sudo systemctl enable docker")
    if rc != 0:
        print("Failed at enabling docker daemon.")
        sys.exit(1)
    rc = os.system("sudo systemctl start docker")
    if rc != 0:
        print("Failed at starting docker daemon.")
        sys.exit(1)

    # for user in users:
    #     rc = os.system("sudo usermod -a -G docker %s" % (user['username']))
    #     if rc != 0:
    #         print("Failed at adding user: %s to docker group" % (user['username']))
    #         sys.exit(1)


# def create_users(users):

#     for user in users:
#         rc = os.system("sudo useradd -u %s %s" % (user['uid'], user['username']))
#         if rc != 0:
#             print("Failed at adding user: %s" % (user['username']))
#             sys.exit(1)

#         rc = os.system("sudo mkdir -p /efs/homes/%s" % (user['username']))
#         if rc != 0:
#             print("Failed at creating home directory for user: %s" % (user['username']))
#             sys.exit(1)

#         rc = os.system('sudo chown %s:%s /efs/homes/%s' % (user['username'], user['username'], user['username']))
#         if rc != 0:
#             print("Failed at changing ownership for: %s" % (user['username']))
#             sys.exit(1)

#         rc = os.system('sudo chmod 6700 /efs/homes/%s' % (user['username']))
#         if rc != 0:
#             print("Failed at changing ownership for: %s" % (user['username']))
#             sys.exit(1)

#         rc = os.system("sudo usermod -d /efs/homes/%s -m %s" % (user['username'], user['username']))
#         if rc != 0:
#             print("Failed at moving home directory for: %s" % (user['username']))
#             sys.exit(1)

#         rc = os.system("sudo su - %s -c 'ssh-keygen -t rsa -N ""' " % (user['username']))
#         if rc != 0:
#             print("Failed at creating private key for: %s" % (user['username']))
#             sys.exit(1)

    #Best way to create services user

# Install s3fs on the master node.
def install_s3fs():
    script = """
sudo sed -i 's/enabled=0/enabled=1/' /etc/yum.repos.d/epel.repo
sudo yum install -y gcc libstdc++-devel gcc-c++ fuse fuse-devel curl-devel libxml2-devel mailcap automake openssl-devel git
git clone https://github.com/s3fs-fuse/s3fs-fuse
cd s3fs-fuse/
./autogen.sh
./configure --prefix=/usr --with-openssl
make
sudo make install    
"""

    rc = os.system(script)
    if rc != 0:
        print("Failed at installing S3FS")
        sys.exit(1)

# Add S3Fs keys as arguments

# Download and install cromwell, setup service and enable cromwell.
def install_cromwell():
    os.makedirs("/opt/cromwell")
    
    rc = os.system("chmod 755 /opt/cromwell")
    if rc != 0:
        print("Failed at changing cromwell directory ownership.")
        sys.exit(1)

    contents = urllib2.urlopen("https://api.github.com/repos/broadinstitute/cromwell/releases/latest").read()
    cromwell_release = json.loads(contents)['assets'][0]
    cromwell_url = cromwell_release['browser_download_url']
    cromwell_name = cromwell_release['name']

    rc = os.system("cd /opt/cromwell && wget %s" % (cromwell_url))
    if rc != 0:
        print("Failed at downloading cromwell.")
        sys.exit(1)

    cromwell_script = """
#!/bin/bash
java8 -Dconfig.file=/opt/cromwell/cromwell.conf -jar /opt/cromwell/{} server >> /tmp/cromwell.log
""".format(cromwell_name)

    with open("/opt/cromwell/run_cromwell_server.sh", "w") as fp:
        fp.write(cromwell_script)

    cromwell_config = urllib2.urlopen("https://").read()

    cromwell_config.replace()

    rc = os.system("chmod +x /opt/cromwell/run_cromwell_server.sh")
    if rc != 0:
        print("Failed at making cromwell script executable.")
        sys.exit(1)

    service_file = """
[Unit]
Description=Starts the Cromwell server

[Service]
Type=simple
ExecStart=/opt/cromwell/run_cromwell_server.sh

[Install]
WantedBy=multi-user.target
"""

    rc = os.system("sudo systemctl enable cromwell")
    if rc != 0:
        print("Failed at enabling cromwell.")
        sys.exit(1)


    rc = os.system("sudo systemctl start cromwell")
    if rc != 0:
        print("Failed at starting cromwell.")
        sys.exit(1)

    #Install cromwell config in (/opt/cromwell/cromwell.conf)

def main():
    instanceid = urllib2.urlopen('http://169.254.169.254/latest/meta-data/instance-id').read()
    instance_type = subprocess.check_output("aws ec2 describe-instances \
                            --instance-id %s \
                            --query 'Reservations[].Instances[].Tags[?Key==`Name`].Value[]' \
                            --output text", 
                            shell=True)

    if instance_type == "Master":
        install_utils()
        install_docker()
        install_s3fs()
        install_glauth()
        install_cromwell()

    else:
        install_docker()
        install_ldap_client()