#!/usr/bin/env python
import subprocess
import sys

with open("/efs/opt/hostname") as fp:
    host = fp.read().rstrip()

with open("/opt/ltpsecret") as fp:
    user = "(&(objectClass=posixAccount)(uid=%s))" % (sys.argv[1])
    s = fp.read().rstrip()
    call = subprocess.check_output(['ldapsearch','-x','-H','ldaps://' + host + ":389",'-D',
                        'cn=admin,ou=admin,dc=pcprod,dc=com', '-b', 'dc=pcprod,dc=com',
                        '-s', 'sub', user, '-w', s, "-o", "ldif-wrap=no"])

print("\n".join([ x.split(": ")[1] for x in call.splitlines() if "sshPublicKey" in x]))