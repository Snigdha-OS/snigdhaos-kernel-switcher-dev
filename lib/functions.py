import os
from os import makedirs
import subprocess
import logging
from logging import Logger
import locale
import shutil
import tomlkit
import sys
import gi
from gi.repository import Gtk
gi.require_version("Gtk", "3.0")
from Kernel import Kernel, CommunityKernel, InstalledKernel

BaseDir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
SudoUsername = os.getlogin()
logger = logging.getLogger("logger")
ch = logging.StreamHandler()
# source: https://stackoverflow.com/questions/3220284/how-to-customize-the-time-format-for-python-logging
formatter = logging.Formatter("%(asctime)s:%(levelname)s > %(message)s", "%Y-%m-%d %H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)
locale.setlocale(locale.LC_ALL, "C.utf-8")
LocalEnv = os.environ
LocalEnv["LC_ALL"] = "C.utf-8"

def permissions(dst):
    try:
        groups = subprocess.run(["sh", "-c", "id " + SudoUsername],shell=False,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=LocalEnv)
        for i in groups.stdout.decode().split(" "):
            if "gid" in i:
                g = i.split("(")[1]
                group = g.replace(")", "".strip())
        subprocess.call(["chown", "-R", SudoUsername + ":" + group, dst],shell=False,env=LocalEnv)
    except Exception as e:
        logger.error("Found error in permissions() ! Type: %s" %e)
HomeDir = "/home/" + str(SudoUsername)
default_ConfigFile = "%s/default/config.toml" %BaseDir
ConfigDir = "%s/.config/snigdhaos-kernel-switcher" %HomeDir
ConfigFile = "%s/.config/snigdhaos-kernel-switcher/config.toml" %ConfigDir

def setupConfig(self):
    try:
        if not os.path.exists(ConfigDir):
            makedirs(ConfigDir)
        if not os.path.exists(ConfigFile):
            shutil.copy(default_ConfigFile,ConfigDir)
            permissions(ConfigDir)
        return readConfig(self)
    except Exception as e:
        logger.error("Found error in setupConfig() ! Type: %s" %e)

SupportedKernelDict = {}
CommunityKernelDict = {}
def readConfig(self):
    try:
        logger.info("Reading config file: %s"%ConfigFile)
        ConfigData = None
        with open(ConfigFile, "rb") as f:
            ConfigData = tomlkit.load(f)
            if ConfigData.get("kernels") and "official" in ConfigData["kernels"] is not None:
                for OfficialKernel in ConfigData["kernels"]["official"]:
                    SupportedKernelDict[OfficialKernel["name"]] = (OfficialKernel["description"], OfficialKernel["headers"])
            if ConfigData.get("kernels") and "community" in ConfigData["kernels"] is not None:
                for CommunityKernel in ConfigData["kernels"]["community"]:
                    CommunityKernelDict[CommunityKernel["name"]] = (CommunityKernel["description"], CommunityKernel["headers"], CommunityKernel["repository"])
            if ConfigData.get("logging") is not None and "loglevel" in ConfigData["logging"] is not None:
                loglevel = ConfigData["logging"]["loglevel"].lower()
                logger.info("Setting LogLevel: %s" %loglevel)
                if loglevel == "debug":
                    logger.setLevel(logging.DEBUG)
                elif loglevel == "info":
                    logger.setLevel(logging.INFO)
                else:
                    logger.warning("Invalid logging level set, use info / debug")
                    logger.setLevel(logging.INFO)
            else:
                logger.setLevel(logging.INFO)
        return ConfigData
    except Exception as e:
        logger.error("Found error in readConfig() ! Type: %s"%e)
        sys.exit(1)

def updateConfig(ConfigData, BootLoader):
    try:
        logger.info("Updating config data...")
        with open(ConfigFile, "w") as f:
            tomlkit.dump(ConfigData, f)
        return True
    except Exception as e:
        logger.error("Found error in updateConfig() ! Type: %s"%e)
        return False

CacheDir = "%s/.cache/snigdhaos-kernel-switcher" % HomeDir
CacheFile = "%s/kernels.toml" % CacheDir
CacheUpdate = "%s/update" % CacheDir
def createCacheDir():
    try:
        if not os.path.exists(CacheDir):
            makedirs(CacheDir)
        logger.info("Cache directory = %s" % CacheDir)
        permissions(CacheDir)
    except Exception as e:
        logger.error("Found error in createCacheDir() ! Type: %s" %e)

LogDir = "/var/log/snigdhaos-kernel-switcher"
EventLogFile = "%s/event.log" %LogDir
def createLogDir():
    try:
        if not os.path.exists(LogDir):
            makedirs(LogDir)
        logger.info("Log directory : %s" %LogDir)
    except Exception as e:
        logger.error("Found error in create_log_dir() ! Type: %s" %e)

import datetime
FetchedKernelsDict = {}
ArchlinuxMirrorArchiveUrl = "https://archive.archlinux.org"
headers = {
    "Content-Type": "text/plain;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Linux x86_64) Gecko Firefox",
}
def writeCache():
    try:
        if len(FetchedKernelsDict) > 0:
            with open(CacheFile, "w", encoding="utf-8") as f:
                f.write('title = "Arch Linux Kernels"\n\n')
                f.write('timestamp = "%s"\n'%datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"))
                f.write('source = "%s"\n\n' % ArchlinuxMirrorArchiveUrl)
                for kernel in FetchedKernelsDict.values():
                    f.write("[[kernel]]\n")
                    f.write('name = "%s"\nheaders = "%s"\nversion = "%s"\nsize = "%s"\nfile_format = "%s"\nlast_modified = "%s"\n\n'% (kernel.name,kernel.headers,kernel.version,kernel.size,kernel.file_format,kernel.last_modified))
            permissions(CacheFile)
    except Exception as e:
        logger.error("Found error in write_cache() ! Type: %s" % e)

CachedKernelsList = []
def refreshCache(self):
    CachedKernelsList.clear()
    if os.path.exists(CacheFile):
        os.remove(CacheFile)
    get_official_kernels(self)

CacheDays = 5
def readCache(self):
    try:
        self.timestamp = None
        with open(CacheFile, "rb") as f:
            data = tomlkit.load(f)
            if len(data) == 0:
                logger.error("%s is empty, delete it and open the app again" % CacheFile)
            name = None
            headers = None
            version = None
            size = None
            last_modified = None
            file_format = None
            if len(data) > 0:
                self.timestamp = data["timestamp"]
                self.cache_timestamp = data["timestamp"]
                if self.timestamp:
                    self.timestamp = datetime.datetime.strptime(self.timestamp, "%Y-%m-%d %H-%M-%S")
                    delta = datetime.datetime.now() - self.timestamp
                    if delta.days >= CacheDays:
                        logger.info("Cache is older than 5 days, refreshing ..")
                        refreshCache(self)
                    else:
                        if delta.days > 0:
                            logger.debug("Cache is %s days old" % delta.days)
                        else:
                            logger.debug("Cache is newer than 5 days")
                        kernels = data["kernel"]
                        if len(kernels) > 1:
                            for k in kernels:
                                if (datetime.datetime.now().year - datetime.datetime.strptime(k["last_modified"], "%d-%b-%Y %H:%M").year <= 2):
                                    CachedKernelsList.append(Kernel(k["name"],k["headers"],k["version"],k["size"],k["last_modified"],k["file_format"]))
                            name = None
                            headers = None
                            version = None
                            size = None
                            last_modified = None
                            file_format = None

                            if len(CachedKernelsList) > 0:
                                sorted(CachedKernelsList)
                                logger.info("Kernels cache data processed")
                        else:
                            logger.error("Cached file is invalid, remove it and try again")
            else:
                logger.error("Failed to read cache file")
    except Exception as e:
        logger.error("Exception in read_cache(): %s" % e)

def getOfficialKernels(self):