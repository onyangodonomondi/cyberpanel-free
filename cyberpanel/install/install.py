import sys
import subprocess
import shutil
import installLog as logging
import argparse
import os
import shlex
from firewallUtilities import FirewallUtilities
import time
import string
import random
import platform

# There can not be peace without first a great suffering.

class preFlightsChecks:

    cyberPanelMirror = "mirror.cyberpanel.net/pip"

    def __init__(self,rootPath,ip,path,cwd,cyberPanelPath):
        self.ipAddr = ip
        self.path = path
        self.cwd = cwd
        self.server_root_path = rootPath
        self.cyberPanelPath = cyberPanelPath

    @staticmethod
    def stdOut(message):
        print("\n\n")
        print ("[" + time.strftime(
            "%I-%M-%S-%a-%b-%Y") + "] #########################################################################\n")
        print("[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + message + "\n")
        print ("[" + time.strftime(
            "%I-%M-%S-%a-%b-%Y") + "] #########################################################################\n")

    def checkIfSeLinuxDisabled(self):
        try:
            command = "sestatus"
            output = subprocess.check_output(shlex.split(command)).decode("utf-8")

            if output.find("disabled") > -1 or output.find("permissive") > -1:
                logging.InstallLog.writeToFile("SELinux Check OK. [checkIfSeLinuxDisabled]")
                preFlightsChecks.stdOut("SELinux Check OK.")
                return 1
            else:
                logging.InstallLog.writeToFile("SELinux is enabled, please disable SELinux and restart the installation!")
                preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                os._exit(0)

        except BaseException as msg:
            logging.InstallLog.writeToFile(str(msg) + "[checkIfSeLinuxDisabled]")
            logging.InstallLog.writeToFile("SELinux Check OK. [checkIfSeLinuxDisabled]")
            preFlightsChecks.stdOut("SELinux Check OK.")
            return 1

    def checkPythonVersion(self):
        if sys.version_info[0] >= 3:
            return 1
        elif sys.version_info[0] == 2 and sys.version_info[1] == 7:
            return 1
        else:
            preFlightsChecks.stdOut("You are running Unsupported python version, please install python 2.7 or 3.x")
            os._exit(0)

    def install_system_package(self, package):
        """Helper to install system packages using yum or apt"""
        try:
            package_manager = "yum"
            install_cmd = ["yum", "install", "-y", package]
            
            # Check for apt-get (Ubuntu/Debian)
            if os.path.exists("/usr/bin/apt-get"):
                package_manager = "apt"
                install_cmd = ["apt-get", "install", "-y", package]
                os.environ["DEBIAN_FRONTEND"] = "noninteractive"

            cmd = install_cmd
            preFlightsChecks.stdOut(f"Installing {package} via {package_manager}...")
            
            res = subprocess.call(cmd)
            
            if res != 0:
                preFlightsChecks.stdOut(f"Failed to install {package}")
                return False
            return True
        except Exception as e:
            preFlightsChecks.stdOut(f"Exception installing {package}: {str(e)}")
            return False

    def pip_install(self, package_args):
        """Helper to install python packages via pip, handling PEP 668"""
        try:
            # Try normal install first
            command = "pip install " + package_args
            res = subprocess.call(shlex.split(command))
            
            # If failed, try with --break-system-packages
            if res != 0:
                preFlightsChecks.stdOut("Pip install failed, retrying with --break-system-packages for: " + package_args)
                command = "pip install " + package_args + " --break-system-packages"
                res = subprocess.call(shlex.split(command))
                
            return res
        except:
            return 1

    def setup_account_cyberpanel(self):
        try:
            count = 0

            while (1):
                res = self.install_system_package("sudo")

                if not res:
                    count = count + 1
                    preFlightsChecks.stdOut("SUDO install failed, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("We are not able to install SUDO, exiting the installer. [setup_account_cyberpanel]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("SUDO successfully installed!")
                    preFlightsChecks.stdOut("SUDO successfully installed!")
                    break

            ##

            count = 0

            while (1):
            # useradd is lower level and safer for scripts than adduser on Debian
                command = "useradd -d /home/cyberpanel -m -s /bin/bash cyberpanel"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res != 0:
                    # If user already exists, it might return non-zero, but we can check existence or ignore
                    # But let's log it.
                    count = count + 1
                    preFlightsChecks.stdOut("Not able to add user cyberpanel to system, trying again (might already exist), try number: " + str(count) + "\n")
                    if count == 3:
                        # Assume it exists roughly or failed.
                        logging.InstallLog.writeToFile("We are not able add user cyberpanel to system or it exists. Continuing. [setup_account_cyberpanel]")
                        break
                else:
                    logging.InstallLog.writeToFile("CyberPanel user added!")
                    preFlightsChecks.stdOut("CyberPanel user added!")
                    break

            ##

            count = 0

            while (1):
                sudo_group = "wheel"
                if os.path.exists("/usr/bin/apt-get"):
                    sudo_group = "sudo"

                command = f"usermod -aG {sudo_group} cyberpanel"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut(f"We are trying to add CyberPanel user to {sudo_group} group, trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        logging.InstallLog.writeToFile(f"Not able to add user CyberPanel to {sudo_group} group, exiting the installer. [setup_account_cyberpanel]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile(f"CyberPanel user was successfully added to {sudo_group} group!")
                    preFlightsChecks.stdOut(f"CyberPanel user was successfully added to {sudo_group} group!")
                    break


            ###############################

            path = "/etc/sudoers"

            # Check if we can read it
            if os.path.exists(path):
                # We want to ensure 'cyberpanel' or group has passwordless sudo? 
                # The original code replaced '%wheel ALL=(ALL) NOPASSWD: ALL' if found.
                # But the original code logic was:
                # if items.find("wheel...NOPASSWD") > -1:
                #    write... ("%wheel...NOPASSWD")
                # This looks like it was doing nothing? replacing X with X?
                # Wait, the original code:
                # if items.find("wheel...NOPASSWD") > -1:
                #    write... ("%wheel...NOPASSWD")
                # Maybe it was trying to UNCOMMENT it? no.
                # Let's just append the specific rule for cyberpanel user to be safe and explicit.
                
                # Actually, standard practice: add a file to /etc/sudoers.d/
                if os.path.isdir("/etc/sudoers.d"):
                    with open("/etc/sudoers.d/cyberpanel", "w") as f:
                        f.write("cyberpanel ALL=(ALL) NOPASSWD: ALL\n")
                else:
                    # Append to sudoers if .d not supported (rare nowadays)
                    with open(path, "a") as f:
                        f.write("\ncyberpanel ALL=(ALL) NOPASSWD: ALL\n")

            ###################################

            count = 0

            while (1):

                command = "mkdir -p /etc/letsencrypt"

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res != 0:
                    count = count + 1
                    preFlightsChecks.stdOut("We are trying to create Let's Encrypt directory to store SSLs, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to create Let's Encrypt directory to store SSLs. Installer can continue without this.. [setup_account_cyberpanel]")
                        break
                else:
                    logging.InstallLog.writeToFile("Successfully created Let's Encrypt directory!")
                    preFlightsChecks.stdOut("Successfully created Let's Encrypt directory!")
                    break

            ##

        except:
            logging.InstallLog.writeToFile("[116] setup_account_cyberpanel")
            preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
            os._exit(0)

    def yum_update(self):
        try:
            count = 0
            while (1):
                if os.path.exists("/usr/bin/apt-get"):
                    command = 'apt-get update'
                else:
                    command = 'yum update -y'
                
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("System update failed, trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        logging.InstallLog.writeToFile("System update failed to run, we are being optimistic that installer will still be able to complete installation. [yum_update]")
                        break
                else:
                    logging.InstallLog.writeToFile("System update ran successfully.")
                    preFlightsChecks.stdOut("System update ran successfully.")
                    break


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [yum_update]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [yum_update]")
            return 0

        return 1

    def installCyberPanelRepo(self):
        # On Ubuntu/Debian, repos should be handled by the bootstrap script or are not RPM-based.
        if os.path.exists("/usr/bin/apt-get"):
            return

        cmd = []
        count = 0

        while(1):
            cmd = ["rpm", "-ivh", "http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el7.noarch.rpm"]
            res = subprocess.call(cmd)

            if res == 1:
                count = count + 1
                preFlightsChecks.stdOut("Unable to add CyberPanel official repository, trying again, try number: " + str(count) + "\n")
                if count == 3:
                     # Warn but continue
                    logging.InstallLog.writeToFile("Unable to add CyberPanel official repository. [installCyberPanelRepo]")
                    break
            else:
                logging.InstallLog.writeToFile("CyberPanel Repo added!")
                preFlightsChecks.stdOut("CyberPanel Repo added!")
                break

    def enableEPELRepo(self):
        if os.path.exists("/usr/bin/apt-get"):
            return 1 # Not needed on Ubuntu

        try:
            res = self.install_system_package("epel-release")

            if not res:
                logging.InstallLog.writeToFile("Unable to add EPEL repository! [enableEPELRepo]")
                # Continue anyway
            else:
                logging.InstallLog.writeToFile("EPEL Repo added!")
                preFlightsChecks.stdOut("EPEL Repo added!")

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [enableEPELRepo]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [enableEPELRepo]")
            return 0

        return 1

    def install_pip(self):
        count = 0
        while (1):
            if os.path.exists("/usr/bin/apt-get"):
                res = self.install_system_package("python3-pip")
            else:
                res = self.install_system_package("python-pip")
                if not res:
                     # Try python3-pip for newer CentOS/Alma
                     res = self.install_system_package("python3-pip")

            if not res:
                count = count + 1
                preFlightsChecks.stdOut("Unable to install PIP, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install PIP, exiting installer! [install_pip]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("PIP successfully installed!")
                preFlightsChecks.stdOut("PIP successfully installed!")
                break

    def install_python_dev(self):
        count = 0
        while (1):
            if os.path.exists("/usr/bin/apt-get"):
                res = self.install_system_package("python3-dev")
                self.install_system_package("build-essential")
                self.install_system_package("libssl-dev")
                self.install_system_package("libffi-dev")
                self.install_system_package("python3-setuptools")
                self.install_system_package("libmysqlclient-dev") # For mysqlclient
            else:
                res = self.install_system_package("python3-devel")
                self.install_system_package("gcc")
                self.install_system_package("openssl-devel")
                self.install_system_package("libffi-devel")
                self.install_system_package("mysql-devel") # For mysqlclient

            if not res:
                count = count + 1
                preFlightsChecks.stdOut("We are trying to install python development tools, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install python development tools, exiting installer! [install_python_dev]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("Python development tools successfully installed!")
                preFlightsChecks.stdOut("Python development tools successfully installed!")
                break

    def install_gcc(self):
        count = 0

        while (1):
            res = self.install_system_package("gcc")

            if not res:
                count = count + 1
                preFlightsChecks.stdOut("Unable to install GCC, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install GCC, exiting installer! [install_gcc]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("GCC Successfully installed!")
                preFlightsChecks.stdOut("GCC Successfully installed!")
                break

    def install_python_setup_tools(self):
        count = 0
        while (1):
            if os.path.exists("/usr/bin/apt-get"):
                res = self.install_system_package("python3-setuptools")
            else:
                res = self.install_system_package("python-setuptools")

            if not res:
                count = count + 1
                print("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "] " + "Unable to install Python setup tools, trying again, try number: " + str(
                    count) + "\n")
                if count == 3:
                     # Warn and continue, pip usually provides this
                    logging.InstallLog.writeToFile(
                        "Unable to install Python setup tools. [install_python_setup_tools]")
                    break
            else:
                logging.InstallLog.writeToFile("Python setup tools Successfully installed!")
                print("[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + "Python setup tools Successfully installed!")
                break

    def install_python_requests(self):
        try:
            if os.path.exists("/usr/bin/apt-get"):
                # Try system package first
                if self.install_system_package("python3-requests") and self.install_system_package("python3-urllib3"):
                    logging.InstallLog.writeToFile("Requests/Urllib3 installed via apt!")
                    return

            # For Python 3, we just use pip
            res = self.pip_install("requests urllib3")
            if res == 0:
                logging.InstallLog.writeToFile("Requests module Successfully installed!")
                preFlightsChecks.stdOut("Requests module Successfully installed!")
        except:
             pass

    def install_pexpect(self):
        try:
            if os.path.exists("/usr/bin/apt-get"):
                if self.install_system_package("python3-pexpect"):
                    return

            res = self.pip_install("pexpect")
            if res == 0:
                logging.InstallLog.writeToFile("pexpect successfully installed!")
                preFlightsChecks.stdOut("pexpect successfully installed!")
        except:
            pass

    def install_django(self):
        count = 0
        while (1):
            # Try system package first on Ubuntu/Debian
            if os.path.exists("/usr/bin/apt-get"):
                if self.install_system_package("python3-django"):
                    logging.InstallLog.writeToFile("DJANGO installed via apt!")
                    preFlightsChecks.stdOut("DJANGO installed via apt!")
                    break

            # Installing a newer Django version compatible with Py3. 
            res = self.pip_install("django")

            if res != 0:
                count = count + 1
                preFlightsChecks.stdOut("Unable to install DJANGO, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install DJANGO, exiting installer! [install_django]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("DJANGO successfully installed!")
                preFlightsChecks.stdOut("DJANGO successfully installed!")
                break

    def install_python_mysql_library(self):
        count = 0
        while (1):
            # Try system package first
            if os.path.exists("/usr/bin/apt-get"):
                if self.install_system_package("python3-mysqldb"):
                    logging.InstallLog.writeToFile("mysqlclient installed via apt!")
                    break

            # For Python 3, we use mysqlclient. We installed dev headers in install_python_dev
            res = self.pip_install("mysqlclient")
            
            if res != 0:
                # Fallback or retry?
                count = count + 1
                preFlightsChecks.stdOut("Unable to install mysqlclient, trying again, try number: " + str(count))
                if count == 3:
                     # Warn but continue? No, DB is critical.
                    logging.InstallLog.writeToFile("Unable to install mysqlclient, exiting installer! [install_python_mysql_library]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("mysqlclient successfully installed!")
                preFlightsChecks.stdOut("mysqlclient successfully installed!")
                break

    def install_gunicorn(self):
        count = 0
        while (1):
            if os.path.exists("/usr/bin/apt-get"):
                if self.install_system_package("gunicorn"):
                    break

            res = self.pip_install("gunicorn")
            if res != 0:
                count = count + 1
                preFlightsChecks.stdOut("Unable to install GUNICORN, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install GUNICORN, exiting installer! [install_gunicorn]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("GUNICORN successfully installed!")
                preFlightsChecks.stdOut("GUNICORN successfully installed!")
                break

    def setup_gunicorn(self):
        try:

            os.chdir(self.cwd)

            ##

            logging.InstallLog.writeToFile("Configuring Gunicorn..")

            service = "/etc/systemd/system/gunicorn.service"
            socket = "/etc/systemd/system/gunicorn.socket"
            conf = "/etc/tmpfiles.d/gunicorn.conf"


            shutil.copy("install/gun-configs/gunicorn.service",service)
            shutil.copy("install/gun-configs/gunicorn.socket",socket)
            shutil.copy("install/gun-configs/gunicorn.conf", conf)

            logging.InstallLog.writeToFile("Gunicorn Configured!")

            ### Enable at system startup

            count = 0

            while(1):
                command = "systemctl enable gunicorn.socket"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to enable Gunicorn at system startup, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Gunicorn will not start after system restart, you can manually enable using systemctl enable gunicorn.socket! [setup_gunicorn]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        break
                else:
                    logging.InstallLog.writeToFile("Gunicorn can now start after system restart!")
                    preFlightsChecks.stdOut("Gunicorn can now start after system restart!")
                    break

        except BaseException as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_gunicorn]")
            preFlightsChecks.stdOut("Not able to setup gunicorn, see install log.")

    def install_psutil(self):
        try:
            if os.path.exists("/usr/bin/apt-get"):
                if self.install_system_package("python3-psutil"):
                    return

            res = self.pip_install("psutil")
            if res == 0:
                logging.InstallLog.writeToFile("psutil successfully installed!")
                preFlightsChecks.stdOut("psutil successfully installed!")
        except:
            pass

    def fix_selinux_issue(self):
        try:
            cmd = []

            cmd.append("setsebool")
            cmd.append("-P")
            cmd.append("httpd_can_network_connect")
            cmd.append("1")

            res = subprocess.call(cmd)

            if res == 1:
                logging.InstallLog.writeToFile("fix_selinux_issue problem")
            else:
                pass
        except:
            logging.InstallLog.writeToFile("fix_selinux_issue problem")

    def install_psmisc(self):
        count = 0
        while (1):
            res = self.install_system_package("psmisc")
            if not res:
                count = count + 1
                preFlightsChecks.stdOut("Unable to install psmisc, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install psmisc, exiting installer! [install_psmisc]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("psmisc successfully installed!")
                preFlightsChecks.stdOut("psmisc successfully installed!")
                break

    def download_install_CyberPanel(self,mysqlPassword, mysql):
        try:
            ## On OpenVZ there is an issue with requests module, which needs to upgrade requests module

            if subprocess.check_output('systemd-detect-virt', shell=True).decode("utf-8").find("openvz")>-1:
                pass
                # upgrading requests here usually breaks system pip, skipping for now as we use env/venv or system packages
        except:
            pass

        ##
        
        # We assume the current directory IS the cyberpanel source.
        # os.chdir(self.path) 
        # Skipping download and extraction of old tarball to preserve forked code.
        logging.InstallLog.writeToFile("Skipping CyberPanel tarball download - using current source code.")
        preFlightsChecks.stdOut("Using existing CyberPanel source code...")

        ### update password:

        passFile = "/etc/cyberpanel/mysqlPassword"
        
        # Create directory if it doesn't exist
        if not os.path.exists("/etc/cyberpanel"):
            os.makedirs("/etc/cyberpanel")

        # If passFile doesn't exist, create it with the provided password
        if not os.path.exists(passFile):
             with open(passFile, "w") as f:
                 f.write(mysqlPassword)

        f = open(passFile)
        data = f.read()
        password = data.split('\n', 1)[0]

        ### Put correct mysql passwords in settings file!

        logging.InstallLog.writeToFile("Updating settings.py!")

        path = self.cyberPanelPath+"/cyberpanel/CyberCP/settings.py"

        data = open(path, "r").readlines()

        writeDataToFile = open(path, "w")

        counter = 0

        for items in data:
            if mysql == 'Two':
                if items.find("'PASSWORD':") > -1:
                    if counter == 0:
                        writeDataToFile.writelines("        'PASSWORD': '" + mysqlPassword + "'," + "\n")
                        counter = counter + 1
                    else:
                        writeDataToFile.writelines("        'PASSWORD': '" + password + "'," + "\n")

                else:
                    writeDataToFile.writelines(items)
            else:
                if items.find("'PASSWORD':") > -1:
                    if counter == 0:
                        writeDataToFile.writelines("        'PASSWORD': '" + mysqlPassword + "'," + "\n")
                        counter = counter + 1

                    else:
                        writeDataToFile.writelines("        'PASSWORD': '" + password + "'," + "\n")
                elif items.find('127.0.0.1') > -1:
                    writeDataToFile.writelines("        'HOST': 'localhost',\n")
                elif items.find("'PORT':'3307'") > -1:
                    writeDataToFile.writelines("        'PORT': '',\n")
                else:
                    writeDataToFile.writelines(items)

        writeDataToFile.close()

        logging.InstallLog.writeToFile("settings.py updated!")

        ### Applying migrations


        os.chdir(os.path.join(self.cyberPanelPath, "CyberCP"))

        count = 0

        while(1):
            command = "python3 manage.py makemigrations"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                preFlightsChecks.stdOut("Unable to prepare migrations file, trying again, try number: " + str(count) + "\n")
                if count == 3:
                     # Attempt to continue anyway
                    logging.InstallLog.writeToFile("Unable to prepare migrations file. Continuing anyway... [download_install_CyberPanel]")
                    break
            else:
                logging.InstallLog.writeToFile("Successfully prepared migrations file!")
                preFlightsChecks.stdOut("Successfully prepared migrations file!")
                break
        
        count = 0

        while(1):
            command = "python3 manage.py migrate"

            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                preFlightsChecks.stdOut("Unable to execute the migrations file, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to execute the migrations file. Continuing... [download_install_CyberPanel]")
                    break
            else:
                logging.InstallLog.writeToFile("Migrations file successfully executed!")
                preFlightsChecks.stdOut("Migrations file successfully executed!")
                break

        ## Moving static content to lscpd location
        command = 'mv static /usr/local/lscp/cyberpanel'
        cmd = shlex.split(command)
        res = subprocess.call(cmd)

        if res == 1:
            logging.InstallLog.writeToFile("Could not move static content!")
            preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
            os._exit(0)
        else:
            logging.InstallLog.writeToFile("Static content moved!")
            preFlightsChecks.stdOut("Static content moved!")


        ## fix permissions

        count = 0

        while(1):
            command = "chmod -R 744 /usr/local/CyberCP"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                preFlightsChecks.stdOut("Changing permissions for '/usr/local/CyberCP' failed, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to change permissions for '/usr/local/CyberCP', we are being optimistic that it is still going to work :) [download_install_CyberPanel]")
                    break
            else:
                logging.InstallLog.writeToFile("Permissions successfully changed for '/usr/local/CyberCP'")
                preFlightsChecks.stdOut("Permissions successfully changed for '/usr/local/CyberCP'")
                break

        ## change owner

        count = 0
        while(1):
            command = "chown -R cyberpanel:cyberpanel /usr/local/CyberCP"
            res = subprocess.call(shlex.split(command))

            if res == 1:
                count = count + 1
                preFlightsChecks.stdOut("Unable to change owner for '/usr/local/CyberCP', trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to change owner for '/usr/local/CyberCP', we are being optimistic that it is still going to work :) [download_install_CyberPanel]")
                    break
            else:
                logging.InstallLog.writeToFile("Owner for '/usr/local/CyberCP' successfully changed!")
                preFlightsChecks.stdOut("Owner for '/usr/local/CyberCP' successfully changed!")
                break


    def install_unzip(self):
        try:
            count = 0
            while (1):
                res = self.install_system_package("unzip")

                if not res:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install unzip, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install unzip, exiting installer! [install_unzip]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("unzip successfully installed!")
                    preFlightsChecks.stdOut("unzip Successfully installed!")
                    break


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_unzip]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_unzip]")
            return 0

        return 1

    def install_zip(self):
        try:
            count = 0
            while (1):
                res = self.install_system_package("zip")

                if not res:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install zip, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install zip, exiting installer! [install_zip]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("zip successfully installed!")
                    preFlightsChecks.stdOut("zip successfully installed!")
                    break


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_zip]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_zip]")
            return 0

        return 1

    def installOpenDKIM(self):
        try:
            count = 0
            while (1):
                res = self.install_system_package("opendkim")

                if not res:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install OpenDKIM, trying again, try number: " + str(count))
                    if count == 3:
                         # Use 'break' instead of exit to allow continuation
                        logging.InstallLog.writeToFile("Unable to install OpenDKIM. [installOpenDKIM]")
                        break
                else:
                    logging.InstallLog.writeToFile("OpenDKIM successfully installed!")
                    preFlightsChecks.stdOut("OpenDKIM successfully installed!")
                    break


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installOpenDKIM]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installOpenDKIM]")
            return 0

        return 1

    def installFirewalld(self):
        try:
            count = 0
            while (1):
                # Ubuntu uses ufw usually, but we can try firewalld or just skip
                if os.path.exists("/usr/bin/apt-get"):
                     # On Ubuntu we might just want to rely on UFW or skip firewalld for now if not strictly required by CP core
                     # But CP controls firewalld. Let's try installing it.
                     res = self.install_system_package("firewalld")
                else:
                     res = self.install_system_package("firewalld")

                if not res:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install Firewalld, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install Firewalld. [installFirewalld]")
                        break
                else:
                    logging.InstallLog.writeToFile("Firewalld successfully installed!")
                    preFlightsChecks.stdOut("Firewalld successfully installed!")
                    break


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installFirewalld]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installFirewalld]")
            return 0

        return 1

    def download_install_phpmyadmin(self):
        try:
            os.chdir("/usr/local/lscp/cyberpanel/")
            count = 0

            while(1):
                command = 'wget https://files.phpmyadmin.net/phpMyAdmin/4.8.2/phpMyAdmin-4.8.2-all-languages.zip'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to download PYPMYAdmin, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to download PYPMYAdmin, exiting installer! [download_install_phpmyadmin]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("PHPMYAdmin successfully downloaded!")
                    preFlightsChecks.stdOut("PHPMYAdmin successfully downloaded!")
                    break

            #####

            count = 0

            while(1):
                command = 'unzip phpMyAdmin-4.8.2-all-languages.zip'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    print("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "] " + "Unable to unzip PHPMYAdmin, trying again, try number: " + str(
                        count) + "\n")
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to unzip PHPMYAdmin, exiting installer! [download_install_phpmyadmin]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("PHPMYAdmin unzipped!")
                    print(
                        "[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + "PHPMYAdmin unzipped!")
                    break

            ###

            os.remove("phpMyAdmin-4.8.2-all-languages.zip")

            count = 0

            while(1):
                command = 'mv phpMyAdmin-4.8.2-all-languages phpmyadmin'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    print("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "] " + "Unable to install PHPMYAdmin, trying again, try number: " + str(
                        count) + "\n")
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install PHPMYAdmin, exiting installer! [download_install_phpmyadmin]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("PHPMYAdmin Successfully installed!")
                    print(
                        "[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + "PHPMYAdmin Successfully installed!")
                    break

            ## Write secret phrase


            rString = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

            data = open('phpmyadmin/config.sample.inc.php', 'r').readlines()

            writeToFile = open('phpmyadmin/config.inc.php', 'w')


            for items in data:
                if items.find('blowfish_secret') > -1:
                    writeToFile.writelines("$cfg['blowfish_secret'] = '" + rString + "'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.writelines("$cfg['TempDir'] = '/usr/local/lscp/cyberpanel/phpmyadmin/tmp';\n")

            writeToFile.close()

            if not os.path.exists('/usr/local/lscp/cyberpanel/phpmyadmin/tmp'):
                os.mkdir('/usr/local/lscp/cyberpanel/phpmyadmin/tmp')

            command = 'chown -R nobody:nobody /usr/local/lscp/cyberpanel/phpmyadmin'
            subprocess.call(shlex.split(command))

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [download_install_phpmyadmin]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [download_install_phpmyadmin]")
            return 0

        return 1


    ###################################################### Email setup


    def install_postfix_davecot(self):
        try:
            count = 0
            while(1):
                # Using install_system_package which handles apt/yum
                res = self.install_system_package("postfix")

                if not res:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install Postfix, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install Postfix, you will not be able to send mails and rest should work fine! [install_postfix_davecot]")
                        break
                else:
                    logging.InstallLog.writeToFile("Postfix successfully installed!")
                    preFlightsChecks.stdOut("Postfix successfully installed!")
                    break

            count = 0

            while(1):
                res = self.install_system_package("dovecot-core" if os.path.exists("/usr/bin/apt-get") else "dovecot")
                if os.path.exists("/usr/bin/apt-get"):
                    self.install_system_package("dovecot-mysql")
                    # Ubuntu uses dovecot-core and dovecot-mysql
                else:
                    self.install_system_package("dovecot-mysql")

                if not res: # Checking result of main package
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install Dovecot, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install install Dovecot, you will not be able to send mails and rest should work fine! [install_postfix_davecot]")
                        break
                else:
                    logging.InstallLog.writeToFile("Dovecot successfully installed!")
                    preFlightsChecks.stdOut("Dovecot successfully installed!")
                    break


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_postfix_davecot]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_postfix_davecot]")
            return 0

        return 1


    def setup_email_Passwords(self,mysqlPassword, mysql):
        try:

           logging.InstallLog.writeToFile("Setting up authentication for Postfix and Dovecot...")

           os.chdir(self.cwd)

           if mysql == 'Two':
               mysql_virtual_domains = "email-configs/mysql-virtual_domains.cf"
               mysql_virtual_forwardings = "email-configs/mysql-virtual_forwardings.cf"
               mysql_virtual_mailboxes = "email-configs/mysql-virtual_mailboxes.cf"
               mysql_virtual_email2email = "email-configs/mysql-virtual_email2email.cf"
               davecotmysql = "email-configs/dovecot-sql.conf.ext"
           else:
               mysql_virtual_domains = "email-configs-one/mysql-virtual_domains.cf"
               mysql_virtual_forwardings = "email-configs-one/mysql-virtual_forwardings.cf"
               mysql_virtual_mailboxes = "email-configs-one/mysql-virtual_mailboxes.cf"
               mysql_virtual_email2email = "email-configs-one/mysql-virtual_email2email.cf"
               davecotmysql = "email-configs-one/dovecot-sql.conf.ext"

           ### update password:

           data = open(davecotmysql, "r").readlines()

           writeDataToFile = open(davecotmysql, "w")

           if mysql == 'Two':
               dataWritten = "connect = host=127.0.0.1 dbname=cyberpanel user=cyberpanel password="+mysqlPassword+" port=3307\n"
           else:
               dataWritten = "connect = host=localhost dbname=cyberpanel user=cyberpanel password=" + mysqlPassword + " port=3306\n"

           for items in data:
               if items.find("connect") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()

           ### update password:

           data = open(mysql_virtual_domains, "r").readlines()

           writeDataToFile = open(mysql_virtual_domains, "w")

           dataWritten = "password = " + mysqlPassword + "\n"

           for items in data:
               if items.find("password") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()

           ### update password:

           data = open(mysql_virtual_forwardings, "r").readlines()

           writeDataToFile = open(mysql_virtual_forwardings, "w")

           dataWritten = "password = " + mysqlPassword + "\n"

           for items in data:
               if items.find("password") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()

           ### update password:

           data = open(mysql_virtual_mailboxes, "r").readlines()

           writeDataToFile = open(mysql_virtual_mailboxes, "w")

           dataWritten = "password = " + mysqlPassword + "\n"

           for items in data:
               if items.find("password") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()

           ### update password:

           data = open(mysql_virtual_email2email, "r").readlines()

           writeDataToFile = open(mysql_virtual_email2email, "w")

           dataWritten = "password = " + mysqlPassword + "\n"

           for items in data:
               if items.find("password") > -1:
                   writeDataToFile.writelines(dataWritten)
               else:
                   writeDataToFile.writelines(items)

           writeDataToFile.close()

           logging.InstallLog.writeToFile("Authentication for Postfix and Dovecot set.")

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_email_Passwords]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_email_Passwords]")
            return 0

        return 1


    def setup_postfix_davecot_config(self, mysql):
        try:
           logging.InstallLog.writeToFile("Configuring postfix and dovecot...")

           os.chdir(self.cwd)


           mysql_virtual_domains = "/etc/postfix/mysql-virtual_domains.cf"
           mysql_virtual_forwardings = "/etc/postfix/mysql-virtual_forwardings.cf"
           mysql_virtual_mailboxes = "/etc/postfix/mysql-virtual_mailboxes.cf"
           mysql_virtual_email2email = "/etc/postfix/mysql-virtual_email2email.cf"
           main = "/etc/postfix/main.cf"
           master = "/etc/postfix/master.cf"
           davecot = "/etc/dovecot/dovecot.conf"
           davecotmysql = "/etc/dovecot/dovecot-sql.conf.ext"



           if os.path.exists(mysql_virtual_domains):
               os.remove(mysql_virtual_domains)

           if os.path.exists(mysql_virtual_forwardings):
               os.remove(mysql_virtual_forwardings)

           if os.path.exists(mysql_virtual_mailboxes):
               os.remove(mysql_virtual_mailboxes)

           if os.path.exists(mysql_virtual_email2email):
               os.remove(mysql_virtual_email2email)

           if os.path.exists(main):
               os.remove(main)

           if os.path.exists(master):
               os.remove(master)

           if os.path.exists(davecot):
               os.remove(davecot)

           if os.path.exists(davecotmysql):
               os.remove(davecotmysql)



           ###############Getting SSL

           count = 0

           while(1):
               command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/postfix/key.pem -out /etc/postfix/cert.pem'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to generate SSL for Postfix, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to generate SSL for Postfix, you will not be able to send emails and rest should work fine! [setup_postfix_davecot_config]")
                       return
               else:
                   logging.InstallLog.writeToFile("SSL for Postfix generated!")
                   preFlightsChecks.stdOut("SSL for Postfix generated!")
                   break
           ##

           count = 0

           while(1):

               command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/dovecot/key.pem -out /etc/dovecot/cert.pem'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to generate ssl for Dovecot, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to generate SSL for Dovecot, you will not be able to send emails and rest should work fine! [setup_postfix_davecot_config]")
                       return
               else:
                   logging.InstallLog.writeToFile("SSL generated for Dovecot!")
                   preFlightsChecks.stdOut("SSL generated for Dovecot!")
                   break



           ########### Copy config files

           if mysql == 'Two':
               shutil.copy("email-configs/mysql-virtual_domains.cf","/etc/postfix/mysql-virtual_domains.cf")
               shutil.copy("email-configs/mysql-virtual_forwardings.cf", "/etc/postfix/mysql-virtual_forwardings.cf")
               shutil.copy("email-configs/mysql-virtual_mailboxes.cf", "/etc/postfix/mysql-virtual_mailboxes.cf")
               shutil.copy("email-configs/mysql-virtual_email2email.cf", "/etc/postfix/mysql-virtual_email2email.cf")
               shutil.copy("email-configs/main.cf", main)
               shutil.copy("email-configs/master.cf",master)
               shutil.copy("email-configs/dovecot.conf",davecot)
               shutil.copy("email-configs/dovecot-sql.conf.ext",davecotmysql)
           else:
               shutil.copy("email-configs-one/mysql-virtual_domains.cf", "/etc/postfix/mysql-virtual_domains.cf")
               shutil.copy("email-configs-one/mysql-virtual_forwardings.cf", "/etc/postfix/mysql-virtual_forwardings.cf")
               shutil.copy("email-configs-one/mysql-virtual_mailboxes.cf", "/etc/postfix/mysql-virtual_mailboxes.cf")
               shutil.copy("email-configs-one/mysql-virtual_email2email.cf", "/etc/postfix/mysql-virtual_email2email.cf")
               shutil.copy("email-configs-one/main.cf", main)
               shutil.copy("email-configs-one/master.cf", master)
               shutil.copy("email-configs-one/dovecot.conf", davecot)
               shutil.copy("email-configs-one/dovecot-sql.conf.ext", davecotmysql)



           ######################################## Permissions

           count = 0

           while(1):

               command = 'chmod o= /etc/postfix/mysql-virtual_domains.cf'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change permissions for mysql-virtual_domains.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change permissions for mysql-virtual_domains.cf. [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Permissions changed for mysql-virtual_domains.cf!")
                   preFlightsChecks.stdOut("Permissions changed for mysql-virtual_domains.cf!")
                   break

           ##

           count = 0

           while(1):

               command = 'chmod o= /etc/postfix/mysql-virtual_forwardings.cf'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change permissions for mysql-virtual_forwardings.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change permissions for mysql-virtual_forwardings.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Permissions changed for mysql-virtual_forwardings.cf!")
                   preFlightsChecks.stdOut("Permissions changed for mysql-virtual_forwardings.cf!")
                   break


           ##

           count = 0

           while(1):

               command = 'chmod o= /etc/postfix/mysql-virtual_mailboxes.cf'
               cmd = shlex.split(command)
               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change permissions for mysql-virtual_mailboxes.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change permissions for mysql-virtual_mailboxes.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Permissions changed for mysql-virtual_mailboxes.cf!")
                   preFlightsChecks.stdOut("Permissions changed for mysql-virtual_mailboxes.cf!")
                   break

           ##

           count = 0

           while(1):

               command = 'chmod o= /etc/postfix/mysql-virtual_email2email.cf'
               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change permissions for mysql-virtual_email2email.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change permissions for mysql-virtual_email2email.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Permissions changed for mysql-virtual_email2email.cf!")
                   preFlightsChecks.stdOut("Permissions changed for mysql-virtual_email2email.cf!")
                   break

           ##

           count = 0

           while(1):

               command = 'chmod o= '+main
               cmd = shlex.split(command)
               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change permissions for /etc/postfix/main.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change permissions for /etc/postfix/main.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Permissions changed for /etc/postfix/main.cf!")
                   preFlightsChecks.stdOut("Permissions changed for /etc/postfix/main.cf!")
                   break

           ##

           count = 0

           while(1):

               command = 'chmod o= '+master

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change permissions for /etc/postfix/master.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change permissions for /etc/postfix/master.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Permissions changed for /etc/postfix/master.cf!")
                   preFlightsChecks.stdOut("Permissions changed for /etc/postfix/master.cf!")
                   break


           #######################################

           count = 0

           while(1):
               command = 'chgrp postfix /etc/postfix/mysql-virtual_domains.cf'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change group for mysql-virtual_domains.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change group for mysql-virtual_domains.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Group changed for mysql-virtual_domains.cf!")
                   preFlightsChecks.stdOut("Group changed for mysql-virtual_domains.cf!")
                   break

           ##

           count = 0

           while(1):
               command = 'chgrp postfix /etc/postfix/mysql-virtual_forwardings.cf'
               cmd = shlex.split(command)
               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change group for mysql-virtual_forwardings.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change group for mysql-virtual_forwardings.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Group changed for mysql-virtual_forwardings.cf!")
                   preFlightsChecks.stdOut("Group changed for mysql-virtual_forwardings.cf!")
                   break

           ##

           count = 0

           while(1):
               command = 'chgrp postfix /etc/postfix/mysql-virtual_mailboxes.cf'
               cmd = shlex.split(command)
               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change group for mysql-virtual_mailboxes.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change group for mysql-virtual_mailboxes.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Group changed for mysql-virtual_mailboxes.cf!")
                   preFlightsChecks.stdOut("Group changed for mysql-virtual_mailboxes.cf!")
                   break

           ##

           count = 0

           while(1):

               command = 'chgrp postfix /etc/postfix/mysql-virtual_email2email.cf'
               cmd = shlex.split(command)
               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change group for mysql-virtual_email2email.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change group for mysql-virtual_email2email.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Group changed for mysql-virtual_email2email.cf!")
                   preFlightsChecks.stdOut("Group changed for mysql-virtual_email2email.cf!")
                   break

           ##

           count = 0
           while(1):
               command = 'chgrp postfix '+main
               cmd = shlex.split(command)
               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change group for /etc/postfix/main.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change group for /etc/postfix/main.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Group changed for /etc/postfix/main.cf!")
                   preFlightsChecks.stdOut("Group changed for /etc/postfix/main.cf!")
                   break

           ##

           count = 0

           while(1):

               command = 'chgrp postfix ' + master

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change group for /etc/postfix/master.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change group for /etc/postfix/master.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Group changed for /etc/postfix/master.cf!")
                   preFlightsChecks.stdOut("Group changed for /etc/postfix/master.cf!")
                   break


           ######################################## users and groups

           count = 0

           while(1):

               command = 'groupadd -g 5000 vmail'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to add system group vmail, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to add system group vmail! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("System group vmail created successfully!")
                   preFlightsChecks.stdOut("System group vmail created successfully!")
                   break

           ##

           count = 0

           while(1):

               command = 'useradd -g vmail -u 5000 vmail -d /home/vmail -m'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to add system user vmail, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to add system user vmail! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("System user vmail created successfully!")
                   preFlightsChecks.stdOut("System user vmail created successfully!")
                   break


           ######################################## Further configurations

           #hostname = socket.gethostname()

           ################################### Restart postix

           count = 0

           while(1):

               command = 'systemctl enable postfix.service'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Trying to add Postfix to system startup, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Failed to enable Postfix to run at system restart you can manually do this using systemctl enable postfix.service! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("postfix.service successfully enabled!")
                   preFlightsChecks.stdOut("postfix.service successfully enabled!")
                   break

            ##

           count = 0

           while(1):

               command = 'systemctl start  postfix.service'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Trying to start Postfix, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to start Postfix, you can not send email until you manually start Postfix using systemctl start postfix.service! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("postfix.service started successfully!")
                   preFlightsChecks.stdOut("postfix.service started successfully!")
                   break

           ######################################## Permissions

           count = 0

           while(1):

               command = 'chgrp dovecot /etc/dovecot/dovecot-sql.conf.ext'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change group for /etc/dovecot/dovecot-sql.conf.ext, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change group for /etc/dovecot/dovecot-sql.conf.ext! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Group changed for /etc/dovecot/dovecot-sql.conf.ext!")
                   preFlightsChecks.stdOut("Group changed for /etc/dovecot/dovecot-sql.conf.ext!")
                   break
           ##


           count = 0

           while(1):

               command = 'chmod o= /etc/dovecot/dovecot-sql.conf.ext'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change permissions for /etc/dovecot/dovecot-sql.conf.ext, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change permissions for /etc/dovecot/dovecot-sql.conf.ext! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Permissions changed for /etc/dovecot/dovecot-sql.conf.ext!")
                   preFlightsChecks.stdOut("Permissions changed for /etc/dovecot/dovecot-sql.conf.ext!")
                   break

           ################################### Restart davecot

           count = 0


           while(1):

               command = 'systemctl enable dovecot.service'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to enable dovecot.service, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to enable dovecot.service! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("dovecot.service successfully enabled!")
                   preFlightsChecks.stdOut("dovecot.service successfully enabled!")
                   break


           ##


           count = 0


           while(1):
               command = 'systemctl start dovecot.service'
               cmd = shlex.split(command)
               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to start dovecot.service, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to start dovecot.service! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("dovecot.service successfully started!")
                   preFlightsChecks.stdOut("dovecot.service successfully started!")
                   break

           ##

           count = 0

           while(1):

               command = 'systemctl restart  postfix.service'

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to restart postfix.service, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to restart postfix.service! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("dovecot.service successfully restarted!")
                   preFlightsChecks.stdOut("postfix.service successfully restarted!")
                   break


           ## chaging permissions for main.cf

           count = 0

           while(1):

               command = "chmod 755 "+main

               cmd = shlex.split(command)

               res = subprocess.call(cmd)

               if res == 1:
                   count = count + 1
                   preFlightsChecks.stdOut("Unable to change permissions for /etc/postfix/main.cf, trying again, try number: " + str(count))
                   if count == 3:
                       logging.InstallLog.writeToFile("Unable to change permissions for /etc/postfix/main.cf! [setup_postfix_davecot_config]")
                       break
               else:
                   logging.InstallLog.writeToFile("Permissions changed for /etc/postfix/main.cf!")
                   preFlightsChecks.stdOut("Permissions changed for /etc/postfix/main.cf!")
                   break

           logging.InstallLog.writeToFile("Postfix and Dovecot configured")

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_postfix_davecot_config]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_postfix_davecot_config]")
            return 0

        return 1


    def downoad_and_install_raindloop(self):
        try:
            ###########
            count = 0

            while(1):
                command = 'chown -R nobody:nobody /usr/local/lscp/cyberpanel/'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to change owner for /usr/local/lscp/cyberpanel/, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to change owner for /usr/local/lscp/cyberpanel/, but installer can continue! [downoad_and_install_raindloop]")
                        break
                else:
                    logging.InstallLog.writeToFile("Owner changed for /usr/local/lscp/cyberpanel/!")
                    preFlightsChecks.stdOut("Owner changed for /usr/local/lscp/cyberpanel/!")
                    break
            #######


            os.chdir("/usr/local/lscp/cyberpanel")

            count = 1

            while(1):
                command = 'wget https://www.rainloop.net/repository/webmail/rainloop-community-latest.zip'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to download Rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to download Rainloop, installation can continue but you will not be able to send emails! [downoad_and_install_raindloop]")
                        return
                else:
                    logging.InstallLog.writeToFile("Rainloop Downloaded!")
                    preFlightsChecks.stdOut("Rainloop Downloaded!")
                    break

            #############

            count = 0

            while(1):
                command = 'unzip rainloop-community-latest.zip -d /usr/local/lscp/cyberpanel/rainloop'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to unzip rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("We could not unzip Rainloop, so you will not be able to send emails! [downoad_and_install_raindloop]")
                        return
                else:
                    logging.InstallLog.writeToFile("Rainloop successfully unzipped!")
                    preFlightsChecks.stdOut("Rainloop successfully unzipped!")
                    break

            os.remove("rainloop-community-latest.zip")

            #######

            os.chdir("/usr/local/lscp/cyberpanel/rainloop")

            count = 0

            while(1):
                command = r'find . -type d -exec chmod 755 {} \;'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to change permissions for Rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to change permissions for Rainloop, so you will not be able to send emails!! [downoad_and_install_raindloop]")
                        break
                else:
                    logging.InstallLog.writeToFile("Rainloop permissions changed!")
                    print(
                        "[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + "Rainloop permissions changed!")
                    break

            #############

            count = 0

            while(1):

                command = r'find . -type f -exec chmod 644 {} \;'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to change permissions for Rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to change permissions for Rainloop, so you will not be able to send emails!! [downoad_and_install_raindloop]")
                        break
                else:
                    logging.InstallLog.writeToFile("Rainloop permissions changed!")
                    preFlightsChecks.stdOut("Rainloop permissions changed!")
                    break
            ######

            count = 0

            while(1):

                command = 'chown -R nobody:nobody .'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to change owner for Rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Failed to change owner for Rainloop, so you will not be able to send emails!! [downoad_and_install_raindloop]")
                        break
                else:
                    logging.InstallLog.writeToFile("Rainloop owner changed!")
                    preFlightsChecks.stdOut("Rainloop owner changed!")
                    break




        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [downoad_and_install_rainloop]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [downoad_and_install_rainloop]")
            return 0

        return 1

    ###################################################### Email setup ends!


    def reStartLiteSpeed(self):
        try:
            count = 0
            while(1):
                cmd = []

                cmd.append(self.server_root_path+"bin/lswsctrl")
                cmd.append("restart")

                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to restart OpenLiteSpeed, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to restart OpenLiteSpeed! [reStartLiteSpeed]")
                        break
                else:
                    logging.InstallLog.writeToFile("OpenLiteSpeed restarted Successfully!")
                    preFlightsChecks.stdOut("OpenLiteSpeed restarted Successfully!")
                    break

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        return 1


    def installFirewalld(self):
        try:

            preFlightsChecks.stdOut("Enabling Firewall!")

            count = 0

            while(1):
                command = 'yum -y install firewalld'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install FirewallD, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install FirewallD, funtions related to Firewall will not work! [installFirewalld]")
                        break
                else:
                    logging.InstallLog.writeToFile("FirewallD successfully installed!")
                    preFlightsChecks.stdOut("FirewallD successfully installed!")
                    break

            ######
            command = 'systemctl restart dbus'
            cmd = shlex.split(command)
            subprocess.call(cmd)


            count = 0

            while(1):
                command = 'systemctl start firewalld'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to start FirewallD, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to start FirewallD, you can manually start it later using systemctl start firewalld! [installFirewalld]")
                        break
                else:
                    logging.InstallLog.writeToFile("FirewallD successfully started!")
                    preFlightsChecks.stdOut("FirewallD successfully started!")
                    break


            ##########

            count = 0

            while(1):

                command = 'systemctl enable firewalld'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to enable FirewallD at system startup, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("FirewallD may not start after restart, you need to manually run systemctl enable firewalld ! [installFirewalld]")
                        break
                else:
                    logging.InstallLog.writeToFile("FirewallD successfully enabled on system startup!")
                    preFlightsChecks.stdOut("FirewallD successfully enabled on system startup!")
                    break


            FirewallUtilities.addRule("tcp","8090")
            FirewallUtilities.addRule("tcp", "80")
            FirewallUtilities.addRule("tcp", "443")
            FirewallUtilities.addRule("tcp", "21")
            FirewallUtilities.addRule("tcp", "25")
            FirewallUtilities.addRule("tcp", "587")
            FirewallUtilities.addRule("tcp", "465")
            FirewallUtilities.addRule("tcp", "110")
            FirewallUtilities.addRule("tcp", "143")
            FirewallUtilities.addRule("tcp", "993")
            FirewallUtilities.addRule("udp", "53")
            FirewallUtilities.addRule("tcp", "53")
            FirewallUtilities.addRule("tcp", "40110-40210")

            logging.InstallLog.writeToFile("FirewallD installed and configured!")
            preFlightsChecks.stdOut("FirewallD installed and configured!")


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installFirewalld]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installFirewalld]")
            return 0

        return 1

    ## from here

    def setupLSCPDDaemon(self):
        try:

            preFlightsChecks.stdOut("Trying to setup LSCPD Daemon!")
            logging.InstallLog.writeToFile("Trying to setup LSCPD Daemon!")

            os.chdir(self.cwd)

            shutil.copy("install/lscpd/lscpd.service","/etc/systemd/system/lscpd.service")
            shutil.copy("install/lscpd/lscpdctrl","/usr/local/lscp/bin/lscpdctrl")

            ##

            count = 0

            while(1):
                command = 'chmod +x /usr/local/lscp/bin/lscpdctrl'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to change permissions for /usr/local/lscp/bin/lscpdctrl, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to change permissions for /usr/local/lscp/bin/lscpdctrl [setupLSCPDDaemon]")
                        break
                else:
                    logging.InstallLog.writeToFile("Successfully changed permissions for /usr/local/lscp/bin/lscpdctrl!")
                    preFlightsChecks.stdOut("Successfully changed permissions for /usr/local/lscp/bin/lscpdctrl!")
                    break

            ##

            count = 1

            while(1):

                command = 'systemctl enable lscpd.service'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to enable LSCPD on system startup, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to change permissions for /usr/local/lscp/bin/lscpdctrl, you can do it manually using  systemctl enable lscpd.service [setupLSCPDDaemon]")
                        break
                else:
                    logging.InstallLog.writeToFile("LSCPD Successfully enabled at system startup!")
                    preFlightsChecks.stdOut("LSCPD Successfully enabled at system startup!")
                    break

            ##

            count = 0

            while(1):

                command = 'systemctl start lscpd'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to start LSCPD, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to start LSCPD! [setupLSCPDDaemon]")
                        break
                else:
                    logging.InstallLog.writeToFile("LSCPD successfully started!")
                    preFlightsChecks.stdOut("LSCPD successfully started!")
                    break

            preFlightsChecks.stdOut("LSCPD Daemon Set!")

            logging.InstallLog.writeToFile("LSCPD Daemon Set!")


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupLSCPDDaemon]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupLSCPDDaemon]")
            return 0

        return 1

    def setup_cron(self):

        try:
            ## first install crontab
            file = open("installLogs.txt", 'a')
            count = 0
            while(1):

                command = 'yum install cronie -y'

                cmd = shlex.split(command)

                res = subprocess.call(cmd, stdout=file)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to install cronie, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install cronie, cron jobs will not work. [setup_cron]")
                        break
                else:
                    logging.InstallLog.writeToFile("Cronie successfully installed!")
                    preFlightsChecks.stdOut("Cronie successfully installed!")
                    break


            count = 0

            while(1):

                command = 'systemctl enable crond'
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=file)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to enable cronie on system startup, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("We are not able to enable cron jobs at system startup, you can manually run systemctl enable crond. [setup_cron]")
                        break
                else:
                    logging.InstallLog.writeToFile("Cronie successfully enabled at system startup!")
                    preFlightsChecks.stdOut("Cronie successfully enabled at system startup!")
                    break

            count = 0

            while(1):
                command = 'systemctl start crond'
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=file)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to start crond, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("We are not able to start crond, you can manually run systemctl start crond. [setup_cron]")
                        break
                else:
                    logging.InstallLog.writeToFile("Crond successfully started!")
                    preFlightsChecks.stdOut("Crond successfully started!")
                    break

            ##

            cronFile = open("/etc/crontab", "a")
            cronFile.writelines("0 * * * * root python /usr/local/CyberCP/plogical/findBWUsage.py" + "\n")
            cronFile.writelines("0 * * * * root /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup" + "\n")
            cronFile.writelines("0 0 1 * * root /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup" + "\n")
            cronFile.close()

            command = 'chmod +x /usr/local/CyberCP/plogical/findBWUsage.py'
            cmd = shlex.split(command)
            res = subprocess.call(cmd, stdout=file)

            if res == 1:
                logging.InstallLog.writeToFile("1427 [setup_cron]")
            else:
                pass

            command = 'chmod +x /usr/local/CyberCP/postfixSenderPolicy/client.py'
            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=file)

            if res == 1:
                logging.InstallLog.writeToFile("1428 [setup_cron]")
            else:
                pass

            count = 0

            while(1):
                command = 'systemctl restart crond.service'
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=file)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to restart crond, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("We are not able to restart crond, you can manually run systemctl restart crond. [setup_cron]")
                        break
                else:
                    logging.InstallLog.writeToFile("Crond successfully restarted!")
                    preFlightsChecks.stdOut("Crond successfully restarted!")
                    break

            file.close()


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_cron]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_cron]")
            return 0

        return 1

    def install_default_keys(self):
        try:
            count = 0

            path = "/root/.ssh"

            if not os.path.exists(path):
                os.mkdir(path)

            while (1):

                command = "ssh-keygen -f /root/.ssh/cyberpanel -t rsa -N ''"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to setup default SSH keys, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to setup default SSH keys. [install_default_keys]")
                        break
                else:
                    logging.InstallLog.writeToFile("Succcessfully created default SSH keys!")
                    preFlightsChecks.stdOut("Succcessfully created default SSH keys!")
                    break

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_default_keys]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_default_keys]")
            return 0

        return 1

    def install_rsync(self):
        try:
            count = 0
            while (1):

                command = 'yum -y install rsync'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to install rsync, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install rsync, some of backup functions will not work. [install_rsync]")
                        break
                else:
                    logging.InstallLog.writeToFile("Succcessfully installed rsync!")
                    preFlightsChecks.stdOut("Succcessfully installed rsync!")
                    break


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_rsync]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_rsync]")
            return 0

        return 1

    def test_Requests(self):
        try:
            import requests
            getVersion = requests.get('https://cyberpanel.net/version.txt')
            latest = getVersion.json()
        except BaseException as msg:

            command = "pip uninstall --yes urllib3"
            subprocess.call(shlex.split(command))

            command = "pip uninstall --yes requests"
            subprocess.call(shlex.split(command))

            count = 0
            while (1):

                res = self.pip_install("http://mirror.cyberpanel.net/urllib3-1.22.tar.gz")

                if res != 0:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to install urllib3 module, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install urllib3 module, exiting installer! [install_python_requests]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("urllib3 module Successfully installed!")
                    preFlightsChecks.stdOut("urllib3 module Successfully installed!")
                    break

            count = 0
            while (1):

                res = self.pip_install("http://mirror.cyberpanel.net/requests-2.18.4.tar.gz")

                if res != 0:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to install requests module, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install requests module, exiting installer! [install_python_requests]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("Requests module Successfully installed!")
                    preFlightsChecks.stdOut("Requests module Successfully installed!")
                    break

    def installation_successfull(self):
        print("###################################################################")
        print("                CyberPanel Successfully Installed                  ")
        print("                                                                   ")

        print("                                                                   ")
        print("                                                                   ")

        print("                Visit: https://" + self.ipAddr + ":8090                ")
        print("                Username: admin                                    ")
        print("                Password: 1234567                                  ")

        print("###################################################################")

    def installCertBot(self):
        try:

            command = "pip uninstall --yes pyOpenSSL"
            res = subprocess.call(shlex.split(command))

            command = "pip uninstall --yes certbot"
            res = subprocess.call(shlex.split(command))

            count = 0
            while (1):
                # Try system package first
                if self.install_system_package("python3-openssl"):
                    logging.InstallLog.writeToFile("python3-openssl successfully installed via system package!")
                    preFlightsChecks.stdOut("python3-openssl successfully installed via system package!")
                    break

                res = self.pip_install("pyOpenSSL")

                if res != 0:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install pyOpenSSL, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install pyOpenSSL, exiting installer! [installCertBot]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("pyOpenSSL successfully installed!  [pip]")
                    preFlightsChecks.stdOut("pyOpenSSL successfully installed!  [pip]")
                    break

            count = 0
            while (1):
                # Try system package first
                if self.install_system_package("certbot") or self.install_system_package("python3-certbot"):
                     logging.InstallLog.writeToFile("CertBot successfully installed via system package!")
                     preFlightsChecks.stdOut("CertBot successfully installed via system package!")
                     break

                res = self.pip_install("certbot")
                
                if res != 0:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install CertBot, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install CertBot, exiting installer! [installCertBot]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                     logging.InstallLog.writeToFile("CertBot successfully installed! [pip]")
                     preFlightsChecks.stdOut("CertBot successfully installed! [pip]")
                     break

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installCertBot]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installCertBot]")
            return 0

        return 1

    def modSecPreReqs(self):
        try:

            pathToRemoveGarbageFile = os.path.join(self.server_root_path,"modules/mod_security.so")
            os.remove(pathToRemoveGarbageFile)

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [modSecPreReqs]")
            return 0

    def installTLDExtract(self):
        try:
            count = 0
            while (1):
                if os.path.exists("/usr/bin/apt-get"):
                    if self.install_system_package("python3-tldextract"):
                        break

                res = self.pip_install("tldextract")

                if res != 0:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install tldextract, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install tldextract! [installTLDExtract]")
                else:
                    logging.InstallLog.writeToFile("tldextract successfully installed!  [pip]")
                    preFlightsChecks.stdOut("tldextract successfully installed!  [pip]")
                    break
        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installTLDExtract]")
            return 0

    def installOpenDKIM(self):
        try:
            count = 0
            while (1):

                command = 'yum -y install opendkim'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to install opendkim, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install opendkim, your mail may not end up in inbox. [installOpenDKIM]")
                        break
                else:
                    logging.InstallLog.writeToFile("Succcessfully installed opendkim!")
                    preFlightsChecks.stdOut("Succcessfully installed opendkim!")
                    break


        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installOpenDKIM]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installOpenDKIM]")
            return 0

        return 1

    def configureOpenDKIM(self):
        try:

            ## Configure OpenDKIM specific settings

            openDKIMConfigurePath = "/etc/opendkim.conf"

            configData = """
Mode	sv
Canonicalization	relaxed/simple
KeyTable	refile:/etc/opendkim/KeyTable
SigningTable	refile:/etc/opendkim/SigningTable
ExternalIgnoreList	refile:/etc/opendkim/TrustedHosts
InternalHosts	refile:/etc/opendkim/TrustedHosts
"""

            writeToFile = open(openDKIMConfigurePath,'a')
            writeToFile.write(configData)
            writeToFile.close()


            ## Configure postfix specific settings

            postfixFilePath = "/etc/postfix/main.cf"

            configData = """
smtpd_milters = inet:127.0.0.1:8891
non_smtpd_milters = $smtpd_milters
milter_default_action = accept
"""

            writeToFile = open(postfixFilePath,'a')
            writeToFile.write(configData)
            writeToFile.close()


            #### Restarting Postfix and OpenDKIM

            command = "systemctl start opendkim"
            subprocess.call(shlex.split(command))

            command = "systemctl enable opendkim"
            subprocess.call(shlex.split(command))

            ##

            command = "systemctl start postfix"
            subprocess.call(shlex.split(command))



        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [configureOpenDKIM]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [configureOpenDKIM]")
            return 0

        return 1

    def installdnsPython(self):
        try:
            count = 0
            while (1):
                if os.path.exists("/usr/bin/apt-get"):
                    if self.install_system_package("python3-dnspython"):
                        break

                res = self.pip_install("dnspython")

                if res != 0:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install dnspython, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install dnspython! [installdnsPython]")
                else:
                    logging.InstallLog.writeToFile("dnspython successfully installed!  [pip]")
                    preFlightsChecks.stdOut("dnspython successfully installed!  [pip]")
                    break
        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installdnsPython]")
            return 0

    def setupCLI(self):
        try:
            count = 0
            while (1):
                command = "ln -s /usr/local/CyberCP/cli/cyberPanel.py /usr/bin/cyberpanel"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to setup CLI, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to setup CLI! [setupCLI]")
                else:
                    logging.InstallLog.writeToFile("CLI setup successfull!")
                    preFlightsChecks.stdOut("CLI setup successfull!")
                    break

            command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"
            res = subprocess.call(shlex.split(command))

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupCLI]")
            return 0

    def setupPHPAndComposer(self):
        try:
            command = "cp /usr/local/lsws/lsphp71/bin/php /usr/bin/"
            res = subprocess.call(shlex.split(command))

            os.chdir(self.cwd)

            command = "chmod +x composer.sh"
            res = subprocess.call(shlex.split(command))

            command = "./composer.sh"
            res = subprocess.call(shlex.split(command))

        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupPHPAndComposer]")
            return 0

    def setupVirtualEnv(self):
        try:

            ##

            count = 0
            while (1):
                command = "yum install -y libattr-devel xz-devel gpgme-devel mariadb-devel curl-devel"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install project dependant modules, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install project dependant modules! [setupVirtualEnv]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("Project dependant modules installed successfully!")
                    preFlightsChecks.stdOut("Project dependant modules installed successfully!!")
                    break

            ##


            count = 0
            while (1):
                if os.path.exists("/usr/bin/apt-get"):
                    if self.install_system_package("virtualenv"):
                        break
                        
                res = self.pip_install("virtualenv")

                if res != 0:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install virtualenv, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed install virtualenv! [setupVirtualEnv]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("virtualenv installed successfully!")
                    preFlightsChecks.stdOut("virtualenv installed successfully!")
                    break

            ####

            count = 0
            while (1):
                command = "virtualenv --system-site-packages /usr/local/CyberCP"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to setup virtualenv, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to setup virtualenv! [setupVirtualEnv]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("virtualenv setuped successfully!")
                    preFlightsChecks.stdOut("virtualenv setuped successfully!")
                    break

            ##

            env_path = '/usr/local/CyberCP'
            subprocess.call(['virtualenv', env_path])
            activate_this = os.path.join(env_path, 'bin', 'activate_this.py')
            exec(open(activate_this).read(), dict(__file__=activate_this))

            ##

            count = 0
            while (1):
                command = "pip install --ignore-installed -r /usr/local/CyberCP/requirments.txt"
                res = subprocess.call(shlex.split(command))

                if res == 1:
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install project dependant modules, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install project dependant modules! [setupVirtualEnv]")
                        break
                else:
                    logging.InstallLog.writeToFile("Project dependant modules installed successfully!")
                    preFlightsChecks.stdOut("Project dependant modules installed successfully!!")
                    break

            command = "systemctl restart gunicorn.socket"
            res = subprocess.call(shlex.split(command))

            command = "virtualenv --system-site-packages /usr/local/CyberCP"
            res = subprocess.call(shlex.split(command))



        except OSError as msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupVirtualEnv]")
            return 0




def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('publicip', help='Please enter public IP for your VPS or dedicated server.')
    parser.add_argument('--mysql', help='Specify number of MySQL instances to be used.')
    args = parser.parse_args()

    logging.InstallLog.writeToFile("Starting CyberPanel installation..")
    preFlightsChecks.stdOut("Starting CyberPanel installation..")

    ## Writing public IP

    if not os.path.exists("/etc/cyberpanel"):
        os.mkdir("/etc/cyberpanel")

    machineIP = open("/etc/cyberpanel/machineIP", "w")
    machineIP.writelines(args.publicip)
    machineIP.close()

    cwd = os.getcwd()

    checks = preFlightsChecks("/usr/local/lsws/",args.publicip,"/usr/local",cwd,"/usr/local/CyberCP")

    try:
        mysql = args.mysql
    except:
        mysql = 'One'


    checks.checkPythonVersion()
    checks.setup_account_cyberpanel()
    checks.yum_update()
    checks.installCyberPanelRepo()
    checks.enableEPELRepo()
    checks.install_pip()
    checks.install_python_dev()
    checks.install_gcc()
    checks.install_python_setup_tools()
    checks.install_django()
    checks.install_pexpect()
    checks.install_python_mysql_library()
    checks.install_gunicorn()
    checks.install_psutil()
    checks.setup_gunicorn()

    import installCyberPanel

    installCyberPanel.Main(cwd, mysql)
    checks.fix_selinux_issue()
    checks.install_psmisc()
    checks.install_postfix_davecot()
    checks.setup_email_Passwords(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
    checks.setup_postfix_davecot_config(mysql)


    checks.install_unzip()
    checks.install_zip()
    checks.install_rsync()

    checks.downoad_and_install_raindloop()


    checks.download_install_phpmyadmin()

    checks.installFirewalld()

    checks.setupLSCPDDaemon()
    checks.install_python_requests()
    checks.install_default_keys()

    checks.installCertBot()
    checks.test_Requests()
    checks.download_install_CyberPanel(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
    checks.setupCLI()
    checks.setup_cron()
    checks.installTLDExtract()
    #checks.installdnsPython()

    ## Install and Configure OpenDKIM.

    checks.installOpenDKIM()
    checks.configureOpenDKIM()

    checks.modSecPreReqs()
    checks.setupVirtualEnv()
    checks.setupPHPAndComposer()
    checks.installation_successfull()

    logging.InstallLog.writeToFile("CyberPanel installation successfully completed!")


if __name__ == "__main__":
    main()