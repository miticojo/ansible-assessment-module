# Ansible Assessment module for RHEL/CENTOS machines

This module allows to run assessment on target machines and reports results in variable files, usable for configuration replica on different target.

System component included:

* **security and authentication**
    * users (with credentials if present)
    * groups
    * limits
    
* **system**
    * sysctl params
    * mounts
    * ntp
    * dns
    * crontab
    
* **application**
    * repositories
    * installed rpm
    * running process
