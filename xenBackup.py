#!/usr/bin/env python

#
# Zero-Downtime XEN VM backup script v2
# Usage: xenBackup.py
#
# 2015-06-09 Mogilowski Sebastian <sebastian@mogilowski.net>
#

import sys, time, os, datetime, urllib2, base64, logging, XenAPI
from logging.handlers import TimedRotatingFileHandler

# --- Settings ---
server='192.168.0.2' # The Pool Master !
user='root'
password='XXXXXXXXXXXX'
path='/path/to/your/backups' # Path to Backup XVA files
bkCount=2 # Number of Backups to store
# --- End Settings ---

# --- Logger ---

logHandler = TimedRotatingFileHandler(filename=path+'/backup.log',when="midnight",interval=2,backupCount=5)
logFormatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logHandler.setFormatter( logFormatter )
logger = logging.getLogger( 'MyLogger' )
logger.addHandler( logHandler )
logger.setLevel( logging.INFO )

# --- End Logger ---

# --- Methods ---
def getOldestFile(directory,vmname):
	dirList = os.listdir(directory)
	sortedDirList = []

	for baseName in dirList:
		fileName = os.path.join(directory,baseName)
		fileAge = os.path.getmtime(fileName)
		fileTuple = (fileAge, fileName, baseName)
		if fileName.endswith('.xva') and baseName.startswith(vmname):
			sortedDirList.append(fileTuple)

	if len(sortedDirList) == 0:
		return ""

	sortedDirList.sort()

	return sortedDirList[0][1]

def countOldestFiles(directory,vmname):
	i = 0
	dirList = os.listdir(directory)
	
	for baseName in dirList:
		fileName = os.path.join(directory,baseName)
		if fileName.endswith('.xva') and baseName.startswith(vmname):
			i += 1
	return i

# --- End Methods ---

# --- Initial checks ---

pid = str(os.getpid())
pidfile = "/tmp/xenbackup.pid"

# Check if script is already running
if os.path.isfile(pidfile):
    print "%s already exists, exiting" % pidfile
    sys.exit()
else:
    file(pidfile, 'w').write(pid)

# Check if path exits
if not os.path.isdir(path):
        print "Backup location don't exits ! %s" % (path)
	logger.error("Backup location don't exits ! %s" % (path))
	os.unlink(pidfile)
	sys.exit(1)

# Check path is writeable
if not os.access(path, os.W_OK):
	print "Backup location isn't writeable ! %s" % (path)
	logger.error("Backup location isn't writeable ! %s" % (path))
	os.unlink(pidfile)
	sys.exit(1)

# --- End initial checks

# Try to connect to xen server and create a session ( with redirection if master server has changed )

try:
	session=XenAPI.Session('https://'+server)
	session.login_with_password(user, password)
except XenAPI.Failure, e:
	if e.details[0]=='HOST_IS_SLAVE':
		try:
			logger.warning("Host %s is slave server." % (server))
			session=XenAPI.Session('https://'+e.details[1])
			session.login_with_password(user, password)
			logger.info("Connected to new master %s " % (e.details[1]))
		except:
			logger.error('Connection to XEN server failed')
			os.unlink(pidfile)
			sys.exit(1)
        else:
		logger.error('Connection to XEN server failed')
		os.unlink(pidfile)
		sys.exit(1)
except:
	logger.error('Connection to XEN server failed')
	os.unlink(pidfile)
	sys.exit(1)

# Loop over all vms and create backups
for vm in session.xenapi.VM.get_all():

        record = session.xenapi.VM.get_record(vm)

        if not(record["is_a_template"]) and not(record["is_control_domain"]) and record["power_state"] == "Running":
		

		print "Starting Backup of: %s" % (record["name_label"])

		# Current Date/Time
		date = datetime.datetime.today()
		date = date.strftime('%Y-%m-%d-%H-%M')

		logger.info("Starting Backup of: %s" % (record["name_label"]))

		# Create new snapshot of VM
		try:
			snapshotName = 'bk_'+record["name_label"]+'_snapshot_'+date
			snapshotVM = session.xenapi.VM.snapshot(vm, snapshotName)
			snapshotRecord = session.xenapi.VM.get_record(snapshotVM)

			logger.info("UUID Snapshot: %s" % (snapshotRecord["uuid"]))

			currentHost = session.xenapi.host.get_record(record["resident_on"])
		except:
			logger.error("Can not create snapshot of VM %s" % (record["name_label"]))
			continue # Try next vm

		# Download File from XenServer Cluster (Use currentHost to prevent SSL Download !)
		localFile = path+'/'+record["name_label"]+'_'+date+'.xva'
		exportURL = 'http://'+currentHost["address"]+'/export?uuid='+snapshotRecord["uuid"]

		request = urllib2.Request(exportURL)
		base64string = base64.encodestring('%s:%s' % (user, password)).replace('\n', '')
		request.add_header("Authorization", "Basic %s" % base64string)

		logger.info("Save Backup: %s" % (localFile))

		try:
			print "Download VM"
			req = urllib2.urlopen(request)
			CHUNK = 16 * 1024
			with open(localFile, 'wb') as fp:
				while True:
					chunk = req.read(CHUNK)
					if not chunk: break
					fp.write(chunk)

		except urllib2.HTTPError, e:
			logger.error("Download Error %s: %s" % (e.code, e.msg))
		
		#Delete snapshot
		# Get VDI ( This is a bug in xenapi ! http://discussions.citrix.com/topic/306141-snapshot-chain-too-long-no-snapshots-visible/ )
		deleteVDIs=[]
		for vbd in snapshotRecord["VBDs"]:
			vbdRecord = session.xenapi.VBD.get_record(vbd)

			if vbdRecord["VDI"] != "OpaqueRef:NULL" and vbdRecord["device"] != 'xvdd': # Filter CD-Drive
				try:
					session.xenapi.VDI.destroy(vbdRecord["VDI"])
				except XenAPI.Failure, e:
					logger.info("Could not delete snapshot vdb of %s" % (record["name_label"]))

		session.xenapi.VM.destroy(snapshotVM)

		logger.info("Finished Backup of: %s" % (record["name_label"]))

		# Delete old backups
		backupCount = countOldestFiles(path,record["name_label"])
		while int(backupCount) > int(bkCount):
			oldestFile = getOldestFile(path,record["name_label"])
			if oldestFile == '':
				break
			logger.info("Delete Backup: %s" % (oldestFile))
			os.remove(oldestFile)
			backupCount = countOldestFiles(path,record["name_label"])


# Close Session
session.xenapi.session.logout()

# Delete PID
os.unlink(pidfile)
