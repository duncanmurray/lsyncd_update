#!/usr/bin/env python

# Author: Duncan Murray 2013

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Import some modules
import pyrax
import re
import argparse
import os
from sys import exit
from pyrax import exceptions as e
import logging
from subprocess import call
import subprocess

# Set default location of pyrax configuration file
CREDFILE = "~/.rackspace_cloud_credentials"
# Set the default location of log files
LOGPATH = "/var/log/lsyncd/"
# Set default metadata key that defines a server installed with lsyncd
METAKEY = "MyGroup0_lsyncd"
# Set default metadata key of your lsyncd configuration group
METAVALUE = "lsyncd_slave"
# Set default location of your lsyncd configuration file
LSYNCDCONF = "/etc/lsyncd.lua"
# Set default location of lsyncd configuration template
TEMPLATE = "/etc/lsyncd.template"

def main():

    # Read in argumants fron command line to over ride defaults
    parser = argparse.ArgumentParser(description=("Automatically update lsyncd configuration"))
    parser.add_argument("-r", "--region", action="store", required=False,
                        metavar="REGION", type=str,
                        help=("Region where your lsyncd configuration group is (defaults"
                              " to 'LON') [ORD, DFW, LON, SYD, IAD]") , choices=["ORD", "DFW", "LON", "SYD", "IAD"],
                        default="LON")
    parser.add_argument("-mk", "--metakey", action="store", required=False,
                        metavar="META_KEY", type=str,
                        help=("Matadata key to search for that identifies lsyncd is installed"), 
                        default=METAKEY)
    parser.add_argument("-mv", "--metavalue", action="store", required=False,
                        metavar="META_VALUE", type=str,
                        help=("Metadata value of your lsyncd configuration group"),
                        default=METAVALUE)
    parser.add_argument("-l", "--lsyncdconf", action="store", required=False,
                        metavar="LSYNCD_FILE", type=str,
                        help=("The location of your lsyncd configuration file"),
                        default=LSYNCDCONF)
    parser.add_argument("-t", "--template", action="store", required=False,
                        metavar="LSYNCD_TEMPLATE", type=str,
                        help=("The location of your lsyncd configuration template"),
                        default=TEMPLATE)
    parser.add_argument("-c", "--credfile", action="store", required=False,
                        metavar="CREDENTIALS_FILE", type=str,
                        help=("The location of your pyrax configuration file"),
                        default=CREDFILE)
    parser.add_argument("-p", "--logpath", action="store", required=False,
                        metavar="LOG_DIRECTORY", type=str,
                        help=("The directory to create log files in"),
                        default=LOGPATH)
    parser.add_argument("-v", "--verbose", action="store_true", required=False,
                        help=("Turn on debug verbosity"),
                        default=False)
    
   
    # Parse arguments (validate user input)
    args = parser.parse_args()

    # Configure log formatting
    logFormatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    rootLogger = logging.getLogger()
    # Check what level we should log with
    if args.verbose:
        rootLogger.setLevel(logging.DEBUG)
    else:
        rootLogger.setLevel(logging.WARNING)
    # Configure logging to console
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)   
    # Configure logging to file
    try:
        fileHandler = logging.FileHandler("{0}/{1}.log".format(args.logpath, os.path.basename(__file__)))
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)
    except IOError:
        rootLogger.critical("Unable to write to log file directory '%s'." % (args.logpath))
        exit(1)

    # Define the authentication credentials file location and request that
    # pyrax makes use of it. If not found, let the client/user know about it.

    # Use a credential file in the following format:
    # [rackspace_cloud]
    # username = myusername
    # api_key = 01234567890abcdef
    # region = LON

    # Set identity type as rackspace
    pyrax.set_setting("identity_type", "rackspace")

    # Test that the pyrax configuration file provided exists
    try:
        creds_file = os.path.expanduser(args.credfile)
        pyrax.set_credential_file(creds_file, args.region)
    # Exit if authentication fails
    except e.AuthenticationFailed:
        rootLogger.critical("Authentication failed. Please check and confirm"
                            "that the API username, key, and region are in place"
                            "and correct.")
        exit(1)
    # Exit if file does not exist
    except e.FileNotFound:
        rootLogger.critical("Credentials file '%s' not found" % (creds_file))
        rootLogger.info("%s", """Use a credential file in the following format:\n
                                 [rackspace_cloud]
                                 username = myuseername
                                 api_key = 01sdf444g3ffgskskeoek0349
                              """
                       )
        exit(2)

    # Define a function to check if we will need to add or remove ip's from lsyncd configuration
    def ipcomp(list1, list2):
        counter = 0
        for ip in list1:
            if ip in list2:
                counter += 1
        if counter == len(list2) and counter == len(list1):
            return True
        else:
            return False

    # Shorten the cloud server invocation string
    cs = pyrax.cloudservers

    # Create a regex to define what a valid IP looks like and compile it
    rexip = re.compile('(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)')

    # Test to see if there are any servers active in our region
    if not cs.servers.list():
        rootLogger.critical("No servers found in region '%s'" % (args.region))
        exit(3)

    # Create an empty list which will be used to store IP's of active servers matching your metadata search
    active_ips = []
    # Get a list of cloud servers
    for server in cs.servers.list():
        # filter out only ACTIVE ones
        if server.status == 'ACTIVE':
            # Check for servers that match both your meta key and value
            if args.metakey in server.metadata and server.metadata[args.metakey] == args.metavalue:
                # Grab the private ip address of matching server(s)
                active_ips.append(server.networks['private'][0])

    # Check that we found some matching key/value pairs from our servers
    if len(active_ips) == 0:
        # If we don't find and matched exit without changing anything
        rootLogger.critical("No active servers found matching key/value pair '%s':'%s'" % (args.metakey, args.metavalue))  
        rootLogger.info("Not making and changes, consider maybe disabling lsyncd")
        exit(4)

    # Test if the lsyncd configuration file exists
    try:
        if os.path.isfile(args.lsyncdconf) == False:
            rootLogger.warning("Creating empty lsyncd configuration file '%s'" % (args.lsyncdconf))
            lfile = open(args.lsyncdconf, 'w')
            lfile.close()
    except IOError:
        rootLogger.critical("Cannot create lsyncd configuration file '%s'" % (args.lsyncdconf))
        exit(5)

    # Open lsyncd configuration file as read only
    lfile = open(args.lsyncdconf, 'r')
    # Read in lsyncd configuration file 
    ltext = lfile.read()
    # Close lsyncd configuration file
    lfile.close()
    
    # Create a new empty list which will be used to store IP's found in lsyncd configuration file
    current_conf_ips = []
    # Match IP's in lsyncd configuration file
    for match in rexip.finditer(ltext):
        # Append the IP's to your list
        current_conf_ips.append(unicode(match.group(0)))
    # Remove duplicate IP's from list
    current_conf_ips = list(set(current_conf_ips)) 

    # Check if IP's in configuration file match active servers
    if ipcomp(active_ips, current_conf_ips) == True:
        # If we don't need to update let the user know
        rootLogger.info("No lsyncd update needed")
        exit(0)
    else:
        # If we need to update let the user know
        rootLogger.warning("Lsyncd configuration file '%s' needs updating" % (args.lsyncdconf))
        rootLogger.info( "Current configured IP's in lsyncd config '%s': '%s'" % (args.lsyncdconf, current_conf_ips))
        rootLogger.info("Servers active matching key/value pair '%s':'%s' in '%s': '%s'" % (args.metakey, args.metavalue, args.region, active_ips))
    
        # Test if lsyncd configuration file is writable
        try:
            lfile = open(args.lsyncdconf, 'w' )
        except IOError:
            rootLogger.critical("Lsyncd configuration file '%s' is not writable" % (args.lsyncdconf))
            exit(6)
        
        # Let the user know that we're going to write a new configuration file
        rootLogger.info("Writing new lsyncd configuration file '%s'" % (args.lsyncdconf))
        
        # Test if lsyncd configuration template exists
        try:
            if os.path.isfile(args.template) == False:
                rootLogger.critical("Unable to find lsyncd template: '%s'" % (args.template))
        except IOError:
            exit(7)
 
        # Read in the settings block from configuration templatea
        with open(args.template) as template_file:
            for line in template_file:
                # Set start of block
                if line.strip() == 'SETTINGS_START':
                    break
            for line in template_file:
                # Set end of block
                if line.strip() == 'SETTINGS_END':
                    break
                # Write lines to file
                lfile.write("%s" % line)
        
        # Read in the sync block(s) from the configuration template
        for ip in active_ips:
            with open(args.template) as template_file:
                for line in template_file:
                    # Set start block
                    if line.strip() == 'SYNC_START':
                        break
                for line in template_file:
                    # Set end block
                    if line.strip() == 'SYNC_END':
                        break
                    # Replace IPREPLACE with active ip's
                    lfile.write("%s" % line.replace('IPREPLACE', ip))
        # Close lsyncd configuration file
        lfile.close()

        # Notify that we need to restart
        rootLogger.warning("Restarting lsyncd service")
        # Set environment variables for subprocess
        my_env ={"PATH": "/usr/bin:/usr/sbin:/bin:/sbin"}

        # Attempt to restart lsyncd
        retcode = subprocess.call(["service lsyncd restart"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=my_env)

        # Successful if return code is 0
        if retcode == 0:
            rootLogger.warning("Lsyncd restart successful")
            exit(0)
        # Failure if non zero return code
        else: 
            rootLogger.critical("Lsyncd restart FAILED. Non zero return code.")
            exit(8)

if __name__ == '__main__':
    main()
