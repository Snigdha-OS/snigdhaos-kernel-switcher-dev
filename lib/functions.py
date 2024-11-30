import os
import locale
import datetime
import requests
import subprocess
from queue import Queue
from threading import Thread
import gi
from gi.repository import GLib
gi.require_version("Gtk", "4.0")
import logging
from logging.handlers import TimedRotatingFileHandler

# ------------ Global Variable Start -------------- #
# Base Directory
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
latest_archlinux_package_search_url = "https://archive.archlinux.org/packages/search/json?name=${PACKAGE_NAME}"
archlinux_mirror_archive_url = "https://archive.archlinux.org/"
headers = {
    "Contect-Type": "text/plain;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Linux x86_64) Gecko Firefox"
}
cache_days = 7
fetch_kernel_dict = {}
supported_kernel_dict = {}
community_kernel_dict = {}
cached_kernel_list = []
community_kernel_list = []
pacman_repos_list = []
process_timeout = 200
sudo_username = os.getlogin()
home = "/home/" + str(sudo_username)

# Pacman Specified
pacman_logfile = "/var/log/pacman.log"
pacman_lockfile = "/var/lib/pacman/db.lck"
pacman_conf_file = "/etc/pacman.conf"
pacman_cache = "/var/cache/pacman/pkg"

# Thread Specified
thread_get_kernels = "thread_get_kernels"
thread_get_community_kernels = "thread_get_community_kernels"
thread_install_community_kernel = "thread_install_community_kernel"
thread_install_archive_kernel = "thread_install_archive_kernel"
thread_check_kernel_state = "thread_check_kernel_state"
thread_uninstall_kernel = "thread_uninstall_kernel"
thread_monitor_messages = "thread_monitor_messages"
thread_refresh_cache = "thread_refresh_cache"
thread_refresh_ui = "thread_refresh_ui"

# Cache Specified
cache_dir = "%s/.cache/snigdhaos-kernel-switcher" %home
cache_file = "%s/kernels.toml" %cache_dir
cache_update = "%s/update" %cache_file

# Log Specified
log_dir = "/var/log/snigdhaos-kernel-switcher"
event_log_file = "%s/event.log" %log_dir

# Configuration Specified
config_file_default = "%s/defaults/config.toml"
config_dir = "%s/.config/snigdhaos-kernel-switcher" %home
config_file = "%s/.config/snigdhaos-kernel-switcher/config.toml" %home

# Logger/Logging Specified
logger = logging.getLogger("logger")
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s:%(levelname)s > %(message)s", "%Y-%m-%d %H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Locale Specified
locale.setlocale(locale.LC_ALL, "C.utf-8")
locale_env = os.environ
locale_env["LC_ALL"] = "C.utf-8"

def permissions(dst):
    try:
        groups = subprocess.run(["sh", "-c", "id " + sudo_username],shell=False,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=locale_env)
        for x in groups.stdout.decode().split(" "):
            if "gid" in x:
                g = x.split("(")[1]
                group = g.replace(")", "").strip()
        subprocess.call(["chown", "-R", sudo_username + ":" + group, dst],shell=False,env=locale_env)
    except Exception as e:
        logger.error("Found Error on permissions(). Exception: %s", e)

def get_response(session,linux_kernel,response_queue,response_content):
    response = requests.get("%s/packages/l/%s" % (archlinux_mirror_archive_url, linux_kernel), headers=headers,allow_redirects=True,timeout=60,stream=True)
    if response.status_code == 200:
        if logger.getEffectiveLevel() == 10:
            logger.debug("Response Code For %s/packages/l/%s = 200 | OK" % (archlinux_mirror_archive_url,linux_kernel))
        if response.text is not None:
            response_content[linux_kernel] = response.text
            response_queue.put(response_content)
    else:
        logger.error("Request Failed!")
        logger.error(response.text)
        response_queue.put(None)

def refreshCache(self):
    cached_kernel_list.clear()
    if os.path.exists(cache_file):
        os.remove(cache_file)
    getOfficialKernels(self)
    writeCache()

def getOfficialKernels(self):
    try:
        if not os.path.exists(cache_file) or self.refreshCache is True:
            session = requests.session()
            response_queue = Queue()
            response_content = {}
            for linux_kernel in supported_kernel_dict:
                logger.info("Fetching Data: %s/packages/l/%s"%(archlinux_mirror_archive_url, linux_kernel))
                Thread(target=get_response,args=(session,linux_kernel,response_queue,response_content), daemon=True).start()

# Get Kernel Update
def getLatestKernelUpdate(self):
    logger.info("Fetching Latest Kernel Versions...")
    try:
        last_update_check = None
        fetch_update = False
        cache_timestamp = None
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                data = f.readlines()[2]
                if len(data) == 0:
                    logger.error("%s empty! Delete and ReOpen the app!" % cache_file)
                if len(data) > 0 and "timestamp" in data.strip():
                    cache_timestamp = data.split("timestamp = ")[1].replace('"', "").strip()
            if not os.path.exists(cache_update):
                last_update_check = datetime.datetime.now().strftime("%y-%m-%d")
                with open(cache_update, mode="w", encoding="utf-8") as f:
                    f.write("%s\n" % last_update_check)
                permissions(cache_dir)
                0
            else:
                with open(cache_update, mode="r", encoding="utf-8") as f:
                    last_update_check = f.read().strip()
                with open(cache_update, mode="w", encoding="utf-8") as f:
                    f.write("%s\n" % datetime.datetime.now().strftime("%Y-%m-%d"))
                permissions(cache_dir)
            logger.info("Last Update Fetch On: %s" % datetime.datetime.now().strptime(last_update_check, "%Y-%m-%d").date())
            if (datetime.datetime.strptime(last_update_check, "%Y-%m-%d").date() < datetime.datetime.now().date()):
                logger.info("Fetching Linux Package Update Data...")
                response = requests.get(latest_archlinux_package_search_url.replace("${PACKAGE_NAME}", "linux"),headers=headers,allow_redirects=True,timeout=60,stream=True)
                if response.status_code == 200:
                    if response.json() is not None:
                        if len(response.json()["results"]) > 0:
                            if response.json()["results"][0]["last_update"]:
                                logger.info("Linux Kernel Last Update: %s" % datetime.datetime.strptime(response.json()["results"][0]["last_update"], "%Y-%m-%dT%H:%M:%S.%f%z").date())
                                if (datetime.datetime.strptime(response.json()["results"][0]["last_update"], "%Y-%m-%dT%H:%M:%S.%f%z").date() >= datetime.datetime.strptime(cache_timestamp, "%Y-%m-%d %H-%M-%S").date()):
                                    logger.info("Linux Package Has Been Updated!")
                                    refreshCache(self)
                                    return True
                                else:
                                    logger.info("Linux Kernel Could Not Be Updated!")
                                    return False
                else:
                    logger.error("Failed To Fetch Valid Response Code!")
                    logger.error(response.text)
            else:
                logger.info("Kernel Update Check Not Required!")
                return False
        else:
            logger.info("No Cache File Found! Refresh The Page!")
            if not os.path.exists(cache_update):
                last_update_check = datetime.datetime.now().strftime("%Y-%m-%d")
                with open(cache_update, mode="w", encoding="utf-8") as f:
                    f.write("%s\n" % last_update_check)
                permissions(cache_dir)
            return False
    except Exception as e:
        logger.error("Found Error on getLatetsKernelUpdate(). Exception: %s" %e)
        return True

                            