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
        required: true
        description:
            - Execute or not users inventory
'''

EXAMPLES = '''
- assessment: users=False
'''


import rpm
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
    ),
    supports_check_mode=False
)

def _fixnl(line):
    return  line.replace("\n", "")

def get_uncomment_lines(file):
    itemlist = []
    if os.path.exists(file):
        with open(file, 'r') as f:
            for line in iter(f):
                if re.match("^[^\s#].*$", line, re.MULTILINE):
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
    return get_uncomment_lines('/etc/sysctl.conf')

def get_fstab():
    return get_uncomment_lines('/etc/fstab')

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


def get_packages():
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
            assessment["packages"] = get_packages()
        if module.params['procs']:
            assessment["procs"] = get_procs()
        if module.params['fstab']:
            assessment["fstab"] = get_fstab()
        if module.params['limits']:
            assessment["limits"] = get_limits()
        module.exit_json(changed=True, msg="Assessment completed. Result available under 'assessment'",
            ansible_facts=dict(assessment=assessment))
    except Exception, ex:
        module.fail_json(msg="Error occurred: %s" % ex)

if __name__ == '__main__':
    main()
