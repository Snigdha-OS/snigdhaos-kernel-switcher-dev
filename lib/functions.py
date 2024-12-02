import os
from os import makedirs
import subprocess
import logging
from logging import Logger
import locale
import gi
from gi.repository import Gtk
gi.require_version("Gtk", "3.0")

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sudousername = os.getlogin()
logger = logging.getLogger("logger")
ch = logging.StreamHandler()
# source: https://stackoverflow.com/questions/3220284/how-to-customize-the-time-format-for-python-logging
formatter = logging.Formatter("%(asctime)s:%(levelname)s > %(message)s", "%Y-%m-%d %H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)
locale.setlocale(locale.LC_ALL, "C.utf-8")
locale_env = os.environ
locale_env["LC_ALL"] = "C.utf-8"

def permissions(dst):
    try:
        groups = subprocess.run(["sh", "-c", "id " + sudousername],shell=False,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=locale_env)
        for i in groups.stdout.decode().split(" "):
            if "gid" in i:
                g = i.split("(")[1]
                group = g.replace(")", "".strip())
        subprocess.call(["chown", "-R", sudousername + ":" + group, dst],shell=False,env=locale_env)
    except Exception as e:
        logger.error("Found error in permissions() ! Type: %s" %e)

