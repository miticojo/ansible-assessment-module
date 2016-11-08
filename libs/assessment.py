#!/usr/bin/python -tt
# -*- coding: utf-8 -*-


DOCUMENTATION = '''
---
module: assessment
author:
    - "Giorgio Crivellari (gcrivell)"
short_description: Generate a complete assessment result in facts
description:
    - Get system info
options:
    users:
        default: true
        description:
            - Execute or not users inventory
    groups:
        default: true
        description:
            - Execute or not groups inventory
    creds:
        default: true
        description:
            - Execute or not user credentials inventory
'''

EXAMPLES = '''
- assessment: users=False
'''

import os
import re


from ansible.module_utils.basic import *
from ansible.module_utils.facts import *


module = AnsibleModule(
    argument_spec  = dict(
        users      = dict(default=True, type="bool"), 
        groups     = dict(default=True, type="bool"),
        creds      = dict(default=True, type="bool"),
        sudoers    = dict(default=True, type="bool"),
        packages   = dict(default=True, type="bool"),
        cron       = dict(default=True, type="bool"),
        sysctl     = dict(default=True, type="bool"),
        procs      = dict(default=True, type="bool"),
        fstab      = dict(default=True, type="bool"),
        limits     = dict(default=True, type="bool"),
        ntp        = dict(default=True, type="bool"),
        dns        = dict(default=True, type="bool"),
        repos       = dict(default=True, type="bool")
    ),
    supports_check_mode=False
)

def _fixnl(line):
    return  line.replace("\n", "")

def get_uncomment_lines(file, commment_char="#"):
    itemlist = []
    if os.path.exists(file):
        with open(file, 'r') as f:
            for line in iter(f):
                if re.match("^[^\s%s].*$" % commment_char, line, re.MULTILINE):
                    itemlist.append(_fixnl(line))
    return itemlist

def get_users():
    itemlist = []
    with open('/etc/passwd', 'r') as f:
        for line in iter(f):
            if int(line.split(":")[2]) > 99:
                itemlist.append({
                    'username': line.split(":")[0],
                    'uid': int(line.split(":")[2]),
                    'gid': int(line.split(":")[3]),
                    'description': line.split(":")[4] if line.split(":")[4] != "" else None,
                    'home': line.split(":")[5] if line.split(":")[5] != "" else None,
                    'shell': _fixnl(line).split(":")[6],
                    'groups': []
                })
    return itemlist

def get_groups(users):
    itemlist = []
    with open('/etc/group', 'r') as f:
        for line in iter(f):
            if int(line.split(":")[2]) > 99:
                user_list = _fixnl(line).split(":")[3].split(',')
                group = {
                    'group_name': line.split(":")[0],
                    'gid': int(line.split(":")[2]),
                    'userlist': user_list if line.split(":")[3] != "" else None,
                }
                if len(user_list) != 0:
                    for u in users:
                        if u["username"] in user_list:
                            u["groups"].append(group["group_name"])
                itemlist.append(group)
    return itemlist

def get_creds(users):
    itemlist = []
    with open('/etc/shadow', 'r') as f:
        for line in iter(f):
            if line.split(":")[0] in [u["username"] for u in users]:
                itemlist.append({
                    'username': line.split(":")[0],
                    'password': line.split(":")[1],
                    'last_pwd_change': line.split(":")[2],
                    'min_age': line.split(":")[3],
                    'max_age': line.split(":")[4],
                    'warn_age': line.split(":")[5],
                    'inact_age': line.split(":")[6],
                    'expires': _fixnl(line).split(":")[7]
                })
    return itemlist

def get_sudoers():
    return get_uncomment_lines('/etc/sudoers')

def get_sysctl():
    itemlist = []
    for line in  get_uncomment_lines('/etc/sysctl.conf'):
        itemlist.append({"name": line.split("=")[0].strip(), "value": line.split("=")[1].strip()})
    return itemlist

def get_fstab():
    return get_uncomment_lines('/etc/fstab')

def get_ntp():
    return get_uncomment_lines('/etc/ntp.conf')

def get_dns():
    return get_uncomment_lines('/etc/resolv.conf', commment_char=";")

def get_limits():
    return get_uncomment_lines('/etc/security/limits.conf')


def get_crontab():
    itemlist = []
    for dirpath, dirnames, filenames in os.walk('/var/spool/cron/'):
        user = {}
        for f in filenames:
            user[f] = get_uncomment_lines(os.path.join(dirpath, f))
            itemlist.append(user)
    return itemlist

def get_repos():
    try:
        import ConfigParser
    except:
        module.fail_json(msg="Module ConfigParser is not present")
        sys.exit(1)

    itemlist = []

    for dirpath, dirnames, filenames in os.walk('/etc/yum.repos.d/'):
        repo = {}
        for f in filenames:
            filename, file_extension = os.path.splitext(f)
            if file_extension == ".repo":
                config = ConfigParser.ConfigParser()
                config.read(os.path.join(dirpath, f))
                itemlist.append(config._sections)
    return itemlist


def get_rpm_nodep():
    import datetime

    itemlist = []
    cmd = os.popen("rpm -qa --queryformat '%{INSTALLTIME}#%{NAME}#%{VERSION}#%{RELEASE}\n'").read()
    for line in cmd.split("\n"):
        items = line.split("#")
        if len(items) == 4:
            itemlist.append({
                "installation_date": datetime.datetime.fromtimestamp(float(items[0])).strftime('%Y-%m-%d %H:%M:%S'),
                "name": items[1],
                "ver": items[2],
                "rel": items[3]
            })
    return itemlist


# No more used cause need RPM modules
def get_packages():
    try:
        import rpm
    except:
        module.fail_json(msg="Module rpm is not present")
        sys.exit(1)

    itemlist = []
    ts = rpm.TransactionSet()
    pkgs = ts.dbMatch()

    for p in pkgs:
        itemlist.append({
            "name": p["name"],
            "ver": p["version"],
            "rel": p["release"]
        })
    return itemlist


def get_procs():
    itemlist = []

    pids = [pid for pid in os.listdir('/proc') if pid.isdigit() and pid > 2]

    for pid in pids:
        try:
            cmd = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read().rstrip(' \t\r\n\0')
            if len(cmd) > 0:
                itemlist.append(str(cmd))
        except IOError:  # proc has already terminated
            continue
    return itemlist

def main():
    try:
        assessment = {}
        if module.params['users']:
            assessment["users"] = get_users()
        if module.params['groups']:
            assessment["groups"] = get_groups(assessment["users"])
        if module.params['creds']:
            assessment["credentials"] = get_creds(assessment["users"])
        if module.params['sudoers']:
            assessment["sudoers"] = get_sudoers()
        if module.params['cron']:
            assessment["crontab"] = get_crontab()
        if module.params["sysctl"]:
            assessment["sysctl"] = get_sysctl()
        if module.params['packages']:
            assessment["packages"] = get_rpm_nodep()
        if module.params['procs']:
            assessment["procs"] = get_procs()
        if module.params['fstab']:
            assessment["fstab"] = get_fstab()
        if module.params['limits']:
            assessment["limits"] = get_limits()
        if module.params['ntp']:
            assessment["ntp"] = get_ntp()
        if module.params['dns']:
            assessment["dns"] = get_dns()
        if module.params['repos']:
            assessment["repos"] = get_repos()
        module.exit_json(changed=False, msg="Assessment completed. Result available under 'assessment'",
                         ansible_facts=dict(assessment=assessment))
    except Exception, ex:
        module.fail_json(msg="Error occurred: %s" % ex)

if __name__ == '__main__':
    main()
