# xenbackup
Python Backupscript for VMs on a Citrix XenServer (or Pool)

The script loops over all running ! VMs on your Server or Pool creates an Snapshop und Download the VM to your backup location.
Zero-Downtime Backup !

You need the XenAPI.py !!!!
Download is available at this locations:
https://pypi.python.org/pypi/XenAPI
https://github.com/xapi-project/xen-api/blob/master/scripts/examples/python/XenAPI.py

You have to configurate the script with the following settings:

server='192.168.0.2' # The Pool Master !

user='root'

password='XXXXXXXXXXXX'

path='/path/to/your/backups' # Path to Backup XVA files

bkCount=2 # Number of Backups to store

If you change the pool master the script locates the new master. If the master is completly offline the script will not work !

You can use Nagios to check the backup. Set 
my $file = "/path/to/your/backups/backup.log";
to the correct path to the logfile of the xenbackup script.
