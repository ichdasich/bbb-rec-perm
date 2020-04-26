#!/usr/bin/python3
import cgi
import os
import re

import psycopg2
conn = psycopg2.connect("dbname=scalelite user=postgres password=PASSWORD host=localhost")

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

def get_meeting_gl_publish(meetingid):
	print("Getting "+meetingid)
	cur = conn.cursor()
	cur.execute("SELECT id FROM recordings WHERE record_id = %s;", (meetingid,))
	recordingid = cur.fetchall()
	if not recordingid:
		print('No record found')
		return 403
	else:
		cur.execute("SELECT value FROM metadata WHERE key = 'gl-listed' AND recording_id = %s;", (recordingid[0][0],))
		gllisted = cur.fetchall()
		if not gllisted:
			return 403
		else:
			if gllisted[0][0] == 'false':
				return 403
			else:
				return 200

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

