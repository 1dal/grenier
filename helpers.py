import subprocess
from pathlib import Path

from logger import *

def duplicity_command(cmd, passphrase):
    if passphrase:
        env_dict = {"PASSPHRASE": passphrase}
    else:
        env_dict = {}
    p = subprocess.Popen(["duplicity", "-v8"] + cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        bufsize=1,
                        env=env_dict)
    for line in iter(p.stdout.readline, b''):
        line = line.decode("utf8").rstrip()
        if line.startswith("Processed"):
            logger.info(".")
    for line in iter(p.stderr.readline, b''):
        line = line.decode("utf8").rstrip()
        if "warning" not in line.lower():
            logger.warning("\t !!! " + line)
    p.communicate()
    logger.info(".")

def attic_command(cmd, passphrase, quiet=False):
    if passphrase:
        env_dict = {"ATTIC_PASSPHRASE": passphrase}
    else:
        env_dict = {}
    p = subprocess.Popen(["attic"] + cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        bufsize=1,
                        env=env_dict)
    output = []
    for line in iter(p.stdout.readline, b''):
        if not quiet:
            logger.info(line.decode("utf8").rstrip())
        output.append(line.decode("utf8").rstrip())
    for line in iter(p.stderr.readline, b''):
        if not quiet:
            logger.warning("\t !!! " + line.decode("utf8").rstrip())
        output.append("\t !!! " + line.decode("utf8").rstrip())
    p.communicate()
    return output

def create_or_check_if_empty(target):
    t = Path(target)
    if not t.exists():
        t.mkdir(parents=True)
        return True
    else:
        return (list(t.rglob('*')) == [])

def list_fuse_mounts():
    p = subprocess.Popen(["mount"],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         bufsize=1)
    mounts = []
    for line in iter(p.stdout.readline, b''):
        line = line.decode("utf8").strip()
        if "atticfs" in line:
            mounts.append(line.split(" ")[2])
    return mounts

def is_fuse_mounted(directory):
    if directory.endswith("/"):
        directory = directory[:-1]
    return directory in list_fuse_mounts()
