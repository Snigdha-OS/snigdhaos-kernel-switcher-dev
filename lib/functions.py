import os
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