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
    getOfficialKernels(self)

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
        logger.error("Found error in readCache() ! Type: %s" % e)

def getResponse(session, LinuxKernel, ResponseQueue, ResponseContent):
    response = session.get("%s/packages/l/%s" % (ArchlinuxMirrorArchiveUrl, LinuxKernel),headers=headers,allow_redirects=True,timeout=60,stream=True)
    if response.status_code == 200:
        if logger.getEffectiveLevel() == 10:
            logger.debug("Response code for %s/packages/l/%s = 200 (OK)"% (ArchlinuxMirrorArchiveUrl, LinuxKernel))
        if response.text is not None:
            ResponseContent[LinuxKernel] = response.text
            ResponseQueue.put(ResponseContent)
    else:
        logger.error("Something went wrong with the request")
        logger.error(response.text)
        ResponseQueue.put(None)

import requests
from queue import Queue
from threading import Thread
def getOfficialKernels(self):
    try:
        if not os.path.exists(CacheFile) or self.refreshCache is True:
            session = requests.session()
            ResponseQueue = Queue()
            ResponseContent = {}
            for LinuxKernel in SupportedKernelDict:
                logger.info("Fetching data from %s/packages/l/%s"% (ArchlinuxMirrorArchiveUrl, LinuxKernel))
                Thread(target=getResponse,args=(session,LinuxKernel,ResponseQueue,ResponseContent),daemon=True).start()
            waitForResponse(ResponseQueue)
            session.close()
            for kernel in ResponseContent:
                parseArchiveHtml(ResponseContent[kernel], kernel)
            if len(FetchedKernelsDict) > 0:
                writeCache()
                readCache(self)
                self.QueueKernels.put(CachedKernelsList)
            else:
                logger.error("Failed to retrieve Linux Kernel list")
                self.QueueKernels.put(None)
        else:
            logger.debug("Reading cache file = %s" % CacheFile)
            readCache(self)
            self.QueueKernels.put(CachedKernelsList)
    except Exception as e:
        logger.error("Found error in getOfficialKernels() ! Type: %s" % e)

def waitForResponse(ResponseQueue):
    while True:
        items = ResponseQueue.get()
        if items is None:
            break
        if len(SupportedKernelDict) == len(items):
            break
        
import re
def parseArchiveHtml(response, LinuxKernel):
    for line in response.splitlines():
        if "<a href=" in line.strip():
            files = re.findall('<a href="([^"]*)', line.strip())
            if len(files) > 0:
                if "-x86_64" in files[0]:
                    version = files[0].split("-x86_64")[0]
                    file_format = files[0].split("-x86_64")[1]
                    url = ("/packages/l/%s" % ArchlinuxMirrorArchiveUrl + "/%s" % LinuxKernel + "/%s" % files[0])
                    if ".sig" not in file_format:
                        if len(line.rstrip().split("    ")) > 0:
                            size = line.strip().split("    ").pop().strip()
                        last_modified = line.strip().split("</a>").pop()
                        for x in last_modified.split("    "):
                            if len(x.strip()) > 0 and ":" in x.strip():
                                # 02-Mar-2023 21:12
                                # %d-%b-Y %H:%M
                                last_modified = x.strip()
                        headers = "%s%s" % (SupportedKernelDict[LinuxKernel][1],version.replace(LinuxKernel, ""))
                        if (version is not None and url is not None and headers is not None and file_format == ".pkg.tar.zst" and datetime.datetime.now().year - datetime.datetime.strptime(last_modified, "%d-%b-%Y %H:%M").year <= 2):
                            ke = Kernel(LinuxKernel,headers,version,size,last_modified,file_format)
                            FetchedKernelsDict[version] = ke
                version = None
                file_format = None
                url = None
                size = None
                last_modified = None
