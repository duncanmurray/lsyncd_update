#!/usr/bin/env python

# Duncan Murray 2013

# Import some modules
import pyrax
import re
import argparse
import os
from sys import exit
from pyrax import exceptions as e


# Location of pyrax configuration file
CREDFILE = "/root/cloudcreds"
# Default metadata key that defines a server installed with lsyncd
METAKEY = "who"
# Default metadata key of your lsyncd configuration group
METAVALUE = "duncan"
# Location of your lsyncd configuration file
LSYNDCONF = "./lsyncd.conf"

def main():
    # Read in argumants cron command line to over ride defaults
    parser = argparse.ArgumentParser(description=("Automatically update lsyncd configuration"))
    parser.add_argument("-r", "--region", action="store", required=False,
                        metavar="region", type=str,
                        help=("Region where your lsyncd configuration group is (defaults"
                              " to 'LON') [ORD, DFW, LON, SYD]") , choices=["ORD", "DFW", "LON", "SYD"],
                        default="LON")
    parser.add_argument("-k", "--metakey", action="store", required=False,
                        metavar="metakey", type=str,
                        help=("Matadata key to search for that identifies lsyncd"
                              " is installed"), 
                        default=METAKEY)
    parser.add_argument("-v", "--metavalue", action="store", required=False,
                        metavar="metavalue", type=str,
                        help=("Metadata value of your lsyncd configuration group"),
                        default=METAVALUE)
    parser.add_argument("-c", "--lsyncdconf", action="store", required=False,
                        metavar="lsyndconf", type=str,
                        help=("The location of your lsyncd configuration file"),
                        default=LSYNDCONF)

    # Parse arguments (validate user input)
    args = parser.parse_args()

    # Define the authentication credentials file location and request that
    # pyrax makes use of it. If not found, let the client/user know about it.

    # Use a credential file in the following format:
    # [rackspace_cloud]
    # username = myusername
    # api_key = 01234567890abcdef
    # region = LON

    # Test that the configuration file provided exists
    try:
        creds_file = os.path.expanduser(CREDFILE)
        pyrax.set_credential_file(creds_file, args.region)
    # Exit if authentication fails
    except e.AuthenticationFailed:
        print ("ERROR: Authentication failed. Please check and confirm "
               "that the API username, key, and region are in place "
               "and correct.")
        exit(1)
    # Exit if file does not exist
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        exit(2)

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
    
    # Define a function to check if any IP's need updating
    def ipcomp(list1, list2):
        for ip in list1:
            if ip in list2:
                # Return true if both lists of IP's match
                return True
            else:
                # Return false if lists of IP's don't match 
                return False
    
    # If list don't match
    if not ipcomp(active_ips, current_conf_ips):
        print "Lsyncd configuration needs updating"
        print "Current Configured IP's:", current_conf_ips
        print "Lsyncd configured servers in group:", active_ips
    
if __name__ == '__main__':
    main()
