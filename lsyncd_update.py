#!/usr/bin/env python

# Duncan Murray 2013

# Import some modules
import pyrax
import re
import argparse
import os
from sys import exit
from pyrax import exceptions as e
import logging
from subprocess import call

# Set default location of pyrax configuration file
CREDFILE = "/root/.rackspace_cloud_credentials"
# Set location of log files
LOGPATH = "/var/log/"
# Set default metadata key that defines a server installed with lsyncd
METAKEY = "lsyncd"
# Set default metadata key of your lsyncd configuration group
METAVALUE = "1"
# Set default location of your lsyncd configuration file
LSYNCDCONF = "/etc/lsyncd.lua"
# Set default location of lsyncd configuration template
TEMPLATE = "/etc/lsyncd.template"

def main():

    # Read in argumants cron command line to over ride defaults
    # No arguments are required and all can be over riden
    parser = argparse.ArgumentParser(description=("Automatically update lsyncd configuration"))
    parser.add_argument("-r", "--region", action="store", required=False,
                        metavar="region", type=str,
                        help=("Region where your lsyncd configuration group is (defaults"
                              " to 'LON') [ORD, DFW, LON, SYD]") , choices=["ORD", "DFW", "LON", "SYD"],
                        default="LON")
    parser.add_argument("-mk", "--metakey", action="store", required=False,
                        metavar="key", type=str,
                        help=("Matadata key to search for that identifies lsyncd is installed"), 
                        default=METAKEY)
    parser.add_argument("-mv", "--metavalue", action="store", required=False,
                        metavar="value", type=str,
                        help=("Metadata value of your lsyncd configuration group"),
                        default=METAVALUE)
    parser.add_argument("-l", "--lsyncdconf", action="store", required=False,
                        metavar="file", type=str,
                        help=("The location of your lsyncd configuration file"),
                        default=LSYNCDCONF)
    parser.add_argument("-t", "--template", action="store", required=False,
                        metavar="file", type=str,
                        help=("The location of your lsyncd configuration template"),
                        default=TEMPLATE)
    parser.add_argument("-c", "--credfile", action="store", required=False,
                        metavar="file", type=str,
                        help=("The location of your pyrax configuration file"),
                        default=CREDFILE)
    parser.add_argument("-v", "--verbose", action="store_true", required=False,
                        help=("Turn on debug verbosity"),
                        default=False)

    # Parse arguments (validate user input)
    args = parser.parse_args()

    # Configure log formatting
    logFormatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    rootLogger = logging.getLogger()
    if args.verbose:
        rootLogger.setLevel(logging.DEBUG)
    else:
        rootLogger.setLevel(logging.WARNING)
    # Configure logging to file
    fileHandler = logging.FileHandler("{0}/{1}.log".format(LOGPATH, os.path.basename(__file__)))
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)
    # Configure loggign to console
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)    

    # Define the authentication credentials file location and request that
    # pyrax makes use of it. If not found, let the client/user know about it.

    # Use a credential file in the following format:
    # [rackspace_cloud]
    # username = myusername
    # api_key = 01234567890abcdef
    # region = LON

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
                                 region = LON
                              """
                       )
        exit(2)

    # Define a function to check if any IP's need updating
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

    # Create an empty list which will be used to store IP's of active servers
    # matching your metadata search
    active_ips = []

    # Geta a list of cloud servers
    for server in cs.servers.list():
        # filter out only ACTIVE ones
        if server.status == 'ACTIVE':
            # Check for servers that match both your meta key and value
            if args.metakey in server.metadata and server.metadata[args.metakey] == args.metavalue:
                # Grab the private ip address of matching server
                active_ips.append(server.networks['private'][0])
    
    # Test if lsyncd configuration file exists
    try:
        if os.path.isfile(args.lsyncdconf) == False:
            rootLogger.warning("%s %s", "Creating empty lsyncd configuration file", args.lsyncdconf)
            lfile = open(args.lsyncdconf, 'w')
            lfile.close()
    except IOError:
        rootLogger.critical("%s %s", "Cannot create lsyncd configuration file", args.lsyncdconf)
        exit(3)

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
    
    # Check if IP's in configuration file match active servers
    if ipcomp(active_ips, current_conf_ips) == True:
        rootLogger.info("No lsyncd update needed")
        exit(0)
    else:
        rootLogger.warning("Lsyncd configuration needs updating")
        rootLogger.info( "%s %s", "Current configured IP's in lsyncd config", current_conf_ips)
        rootLogger.info("%s %s", "Lsyncd servers active in lsyncd group", active_ips)
    
        # Test if lsyncd configuration file is writable
        try:
            lfile = open(args.lsyncdconf, 'w' )
        except IOError:
            rootLogger.critical("%s %s %s", "Lsyncd configuration file", args.lsyncdconf, "is not writable")
            exit(4)
        
        rootLogger.info("Writing new lsyncd configuration file")
        
        # Test if lsyncd configuration template exists
        try:
            if os.path.isfile(args.template) == False:
                rootLogger.critical("%s %s", "Unable to find lsyncd template", args.template)
        except IOError:
            exit(5)
 
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
        with open(args.template) as template_file:
            for ip in active_ips:
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
                lfile.close()

        # Restart lsyncd process
        rootLogger.warning("Restarting lsyncd service")
        call(["/usr/sbin/service", "cron", "restart"])

if __name__ == '__main__':
    main()
