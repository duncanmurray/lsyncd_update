lsyncd_update
=============

An automatic layncd update tool. This tool is used to create an lsyncd configuration file when new Rackspace Cloud Servers are created. It uses metadata key/value pairs to determine if a server should be added into the lsyncd configuration file. 

```
usage: lsyncd_update.py [-h] [-r REGION] [-mk META_KEY] [-mv META_VALUE]
                        [-l LSYNCD_FILE] [-t LSYNCD_TEMPLATE]
                        [-c CREDENTIALS_FILE] [-p LOG_DIRECTORY] [-v]

optional arguments:
  -h, --help            show this help message and exit
  -r REGION, --region REGION
                        Region where your lsyncd configuration group is
                        (defaults to 'LON') [ORD, DFW, LON, SYD]
  -mk META_KEY, --metakey META_KEY
                        Matadata key to search for that identifies lsyncd is
                        installed
  -mv META_VALUE, --metavalue META_VALUE
                        Metadata value of your lsyncd configuration group
  -l LSYNCD_FILE, --lsyncdconf LSYNCD_FILE
                        The location of your lsyncd configuration file
  -t LSYNCD_TEMPLATE, --template LSYNCD_TEMPLATE
                        The location of your lsyncd configuration template
  -c CREDENTIALS_FILE, --credfile CREDENTIALS_FILE
                        The location of your pyrax configuration file
  -p LOG_DIRECTORY, --logpath LOG_DIRECTORY
                        The directory to create log files in
  -v, --verbose         Turn on debug verbosity

```

####PREREQUISITS:

1. Lsyncd installed on master server
2. Public SSH key added to authorized_keys file in server image or inject it as personality
3. Meta data key/value pairs on servers created

####INSTALLATION:

1. Download lsyncd.update.py
```
git clone https://github.com/duncanmurray/lsyncd_update.git \
&& cp lsyncd_upate/lsyncd.template /etc/lsyncd.template \
&& cp lsyncd_update/lsyncd_update.py /usr/local/sbin/lsyncd_update.py
```

2. Download and install pyrax
```
pip install pyrax
```
4. Create pyrax configuration file "~/.rackspace_cloud_credentials" 
```
[rackspace_cloud]
username = myusername
api_key = 01234567890abcdef
```
5. Create cronjob to run lsyncd_update.py
```
*/2 * * * * /usr/local/sbin/lsyncd_update.py -v
```
Or better yet use flock until this script it turned into a deamon. 
```
*/2 * * * * /usr/bin/flock -n /var/lock/lsyncd_update.py.lock -c "/usr/local/sbin/lsyncd_update.py -v"
```
6. Don't forget to rotate your logs if you havn't already. A sample lsyncd log rotation script for `/etc/logrotate.d/lsyncd`.
```
/var/log/lsyncd/*log {
    missingok
    notifempty
    sharedscripts
    postrotate
    if [ -f /var/lock/lsyncd ]; then
      /sbin/service lsyncd restart > /dev/null 2>/dev/null || true
    fi
    endscript
}
```        
####OPTIONS EXPLANATION:

Although no options are required to be passed to the program the defaults can be over ridden with the below flags.


######-h, --help
Shows a help message about the commands options
    
######-r <region>, --region <region>
Select the Rackspace data center of the servers you want to automatically update an lsyncd configuration file for.
    
######-mk <key>, --metakey <key>
Set the metadata key that is common to all your cloud servers in the same working group. For example this could be `WebServers`. The default if none is provided is `MyGroup0`.

######-mv <value>, --metavalue <value>
Set the metadata value that is paired with the key that you provided. For example this could be `lsyncd_ON`. The default value if none is provided is `lsyncd`.
    
######-l <file>, --lsyncdconf <file>
Set the location where you want to write your lsyncd configuration. This can be different depending on the operating system. The default location is `/etc/lsyncd.lua`.
    
######-t <file>, --template <file>
Set the location of your lsyncd configuration template. Since this program was designed to work with multiple versions of lsyncd, you must provide a file that stores the lsyncd settigns and the sync blocks to use. This allows you to setup multiple directories to watch. The settings block starts when a line is found containing only `SETTINGS_START`. The end of the settings block is defines by a line containing `SETTINGS_END`. The sync block starts when a line is found containing `SYNC_START` and ends with a line containing only `SYNC_END`. The program will search for `IPREPLACE` in the sync block and replace it with he IP of each active server. You only need to create one sync block for each directory watched and the script will populate the lsyncd configuration file with one for each active server. The default location of the lsyncd template file is "/etc/lsyncd.template"

######-l <file>, --lsyncdconf <file>
Set the location where to write the lsyncd configuration file. The default location is `/etc/lsyncd.lua`. Depending on your operating system this may be different.
    
######-c <file>, --credfile <file>
Set the location of your pyrax credentials file. This will store your username and API key that is associated with your account. The default location is `~/.rackspace_cloud_credentials`.

###### -p <directory>, --logpath <directory>
Set the directory to log output from the script to. It must exist and be writable by the user running the script. The default location in `/var/log/lsyncd/`.
    
######-v, --verbose
Turn on verbosity. By default logs are written to both the terminal and `/var/log/lsyncd_update.py.log`. Turning on verbose output changes the logging level from `WARNING` to `DEBUG`.
