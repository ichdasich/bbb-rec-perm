#!/usr/bin/python3
import cgi
import os
import re

def parse_url(url=''):
	r = re.compile(r'[0-9a-f]{40}-[0-9]{13}')
	t = re.compile(r'^/presentation/[0-9a-f]{40}-[0-9]{13}/presentation/[0-9a-f]{40}-[0-9]{13}/thumbnails/(thumb-[1-3].png|images/favicon.png)$')
	try:
		thumb = t.findall(url)
		if thumb:
			logfile.write('Thumbnail found\n')
			return False
		else:
			meetingid = r.findall(url)[0]
			return meetingid
	except:
		return False	

def get_meeting_gl_publish(meetingid, recording_path='/var/bigbluebutton/published/presentation/'):
	try:
		metadata = open(recording_path+'/'+meetingid+'/metadata.xml', 'r')
		for line in metadata:
			if "gl-listed" in line:
				if not "false" in line:
					return 200
				else:
					return 403
	except:
		return 403

def ret_auth(authcode=403):
	if authcode == 200:
		print("Content-Type: text/html")
		print("")
	else:
		print('Status: 403 Forbidden\r\n\r\n')

meetingid = parse_url(os.environ['HTTP_X_ORIGINAL_URI'])
if meetingid:
	retcode = get_meeting_gl_publish(meetingid)
	ret_auth(retcode)
else:
	ret_auth(200)

