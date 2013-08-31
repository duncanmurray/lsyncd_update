lsyncd_update
=============

An automatic layncd update tool. This tool is used an lsyncd configuration file when new Rackspace Cloud Servers are created that have a predefines metadata key/value pair. 

usage: lsyncd_update.py [-h] [-r region] [-mk key] [-mv value] [-l file] [-t file] [-c file] [-v]

Automatically update lsyncd configuration

optional arguments:
  -h, --help            show this help message and exit
  -r region, --region region
                        Region where your lsyncd configuration group is
                        (defaults to 'LON') [ORD, DFW, LON, SYD]
  -mk key, --metakey key
                        Matadata key to search for that identifies lsyncd is
                        installed
  -mv value, --metavalue value
                        Metadata value of your lsyncd configuration group
  -l file, --lsyncdconf file
                        The location of your lsyncd configuration file
  -t file, --template file
                        The location of your lsyncd configuration template
  -c file, --credfile file
                        The location of your pyrax configuration file
  -v, --verbose         Turn on debug verbosity

PREREQUISITS:

1. Lsyncd installed on master server
2. Public SSH key added to authorized_keys file in server image or inject it as personality
3. Meta data key/value pairs on servers created

INSTALLATION:

1. Download lsyncd.update.py
    ```
    git clone git@github.com:duncanmurray/lsyncd_update.git && cp lsyncd_upate/lsyncd.template /etc/lsyncd.template \
    && cp lsyncd_upate/update_lsyncd.py /usr/local/sbin/update_lsyncd.py
    ```
2. Download and install pyrax
    pip install pyrax
4. Create pyrax configuration file "/root/.rackspace_cloud_credentials" 
    ```
    [rackspace_cloud]
    username = myusername
    api_key = 01234567890abcdef
    ```
5. Create cronjob to run update_lsyncd.py
    */2 * * * * /usr/local/sbin/update_lsyncd.py
        
OPTIONS EXPLANATION:

Although no options are required to be passed to the program the defaults can be over ridden with the below flags.

-h, --help
    Shows a help message about the commands options
    
-r <region>, --region <region>
    Select the Rackspace data center of the servers you want to automatically update an lsyncd configuration file for.
    
-mk <key>, --metakey <key>
    Set the metadata key that is common to all your cloud servers in the same working group. For example this could be "WebServers". The default if none is provided is "lsyncd".

-mv <value>, --metavalue <value>
    Set the metadata value that is paired with the key that you provided. For example this could be "lsyncd_ON". The default value if none is provided is "1".
    
-l <file>, --lsyncdconf <file>
    Set the location where you want to write your lsyncd configuration. This can be different depending on the operating system. The default location is "/etc/lsyncd.lua".
    
-t <file>, --template <file>
    Set the location of your lsyncd configuration template. Since this program was designed to work with multiple versions of lsyncd, you must provide a file that stores the lsyncd settigns and the sync blocks to use. This allows you to setup multiple directories to watch. 
    The settings block starts when a line is found containing only "SETTINGS_START". The end of the settings block is defines by a line containing "SETTINGS_END". The sync block starts when a line is found containing "SYNC_START" and ends with a line containing only "SYNC_END". The program will search for "IPREPLACE" in the sync block and replace it with he IP of each active server. 
    You only need to create one sync block for each directory watched and the script will populate the lsyncd configuration file with one for each active server.
    The default location of the lsyncd template file is "/etc/lsyncd.template"

-l <file>, --lsyncdconf <file>
    Set the location where to write the lsyncd configuration file. The default location is "/etc/lsyncd.lua". Depending on your operating system this may be different.
    
-c <file>, --credfile <file>
    Set the location of your pyrax credentials file. This will store your username and API key that is associated with your account. The default location is "/root/.rackspace_cloud_credentials".
    
-v, --verbose
    Turn on verbosity. By default logs are written to both the terminal and "/var/log/lsyncd_update.py.log". Turning on verbose output changes the logging level from WARNING to DEBUG.
