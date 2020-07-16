#!/usr/bin/python3
import cgi
import os
import re
import base64
import bcrypt

import psycopg2
conn_auth = psycopg2.connect("dbname=greenlight_production user=postgres password=PASSWORD host=localhost")
conn = psycopg2.connect("dbname=scalelite user=postgres password=PASSWORD host=localhost")

# gl-listed metadata; Default only true (public in FL) and false (unlisted in
# GL are available. If you do not want to use one of these set them to 'DISABLED'

# Public: Access to recording without authentication
PUBLIC_VALUE = 'true'

# GL AUTH: Allow access only to users with a GL account
GL_AUTH_VALUE = 'unlisted'

# GL USER: Allow access only to the owner of the recording
GL_USER_PRIV_VALUE = 'DISABLED'

# GL SHARE: Allow access only to the owner and users they shared the room with
GL_USER_SHARE_VALUE = 'false'



def parse_url(url=''):
	r = re.compile(r'[0-9a-z]{40}-[0-9]{13}')
	t = re.compile(r'^/presentation/[0-9a-z]{40}-[0-9]{13}/presentation/[0-9a-z]{40}-[0-9]{13}/thumbnails/(thumb-[1-3].png|images/favicon.png)$')
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

def get_credentials(environ):
	http_auth = environ['HTTP_AUTHORIZATION'].split()[-1].encode('ascii')
	credentials = base64.decodestring(http_auth).decode('ascii')
	user = credentials.split(':')[0]
	pswd = ':'.join(credentials.split(':')[1:])
	return user, pswd

def authenticate_gl_db(user, pswd):
	if not user or not pswd:
		return False
	cur = conn_auth.cursor()
	
	cur.execute("SELECT email,password_digest FROM users WHERE email = %s;", (user,))
	res = cur.fetchall()
	
	if not res:
		return False
	
	h = res[0][1]
	salt = h[:29].encode('ascii')
	h_user = bcrypt.hashpw(pswd.encode('ascii'), salt).decode('ascii')
	
	if h_user == h:
		return True
	else:
		return False

	return False

def get_meeting_bbbid(meetingid):
	cur = conn.cursor()
	cur.execute("SELECT meeting_id FROM recordings WHERE record_id = %s;", (meetingid,))
	recordingid = cur.fetchall()
	
	if recordingid:
		return recordingid[0][0]
	else:
		return False


# checks if an authenticating user is the owner of a room
def check_owner(meetingid, user):
	bbbid = get_meeting_bbbid(meetingid)
	if not bbbid:
		return False
	cur = conn_auth.cursor()
	
	# Get owner of room
	cur.execute("SELECT user_id FROM rooms WHERE bbb_id = %s;", (bbbid,))
	res = cur.fetchall()
	
	if not res:
		return False
	
	# get mailaddr of owner
	cur.execute("SELECT email FROM users WHERE id = %s;", (res[0][0],))
	res = cur.fetchall()
	
	
	if not res:
		return False
	
	if res[0][0] == user:
		return True
	
	return False

# checks if an authenticating user is the owner of a room
def check_shared(meetingid, user):
	bbbid = get_meeting_bbbid(meetingid)
	if not bbbid:
		return False
	cur = conn_auth.cursor()
	
	cur.execute("SELECT id FROM rooms WHERE bbb_id = %s;", (bbbid,))
	res = cur.fetchall()
	
	if not res:
		return False
	
	cur.execute("SELECT user_id FROM shared_accesses WHERE room_id = %s;", (res[0][0],))
	res = cur.fetchall()
	
	if not res:
		return False
	
	
	for uid in res:
		cur.execute("SELECT email FROM users WHERE id = %s;", (uid[0],))
		tmp_res = cur.fetchall()
		
		if not tmp_res:
			return False
		
		if tmp_res[0][0] == user:
			return True
	
	return False

# Method for cases where you are not using scalelite
def get_meeting_gl_publish(meetingid):
	cur = conn.cursor()
	cur.execute("SELECT id FROM recordings WHERE record_id = %s;", (meetingid,))
	recordingid = cur.fetchall()
	
	if not recordingid:
		return 403
	else:
		cur.execute("SELECT value FROM metadata WHERE key = 'gl-listed' AND recording_id = %s;", (recordingid[0][0],))
		gllisted = cur.fetchall()
		if not gllisted:
			return 403
		else:
			if PUBLIC_VALUE == gllisted[0][0]:
				return 200
			if GL_AUTH_VALUE == gllisted[0][0]:
				return "MATCH_ALL"
			if GL_USER_PRIV_VALUE == gllisted[0][0]:
				return "MATCH_USER"
			if GL_USER_SHARE_VALUE == gllisted[0][0]:
				return "MATCH_SHARED"
			return 403
	#except:
		#return 403

def ret_auth(authcode=403):
	if authcode == 200:
		print("Content-Type: text/html")
		print("")
	elif authcode == 401:
		print('Status: 401 Unauthorized\r\nWWW-Authenticate: Basic realm="Log in to view private recording"\r\n\r\n')
	else:
		print('Status: 403 Forbidden\r\n\r\n')

meetingid = parse_url(os.environ['HTTP_X_ORIGINAL_URI'])

if meetingid:
	retcode = get_meeting_gl_publish(meetingid)
	# If not failure/public
	if not retcode == 403 and not retcode == 200:
		authenticated = False
		# Try to get credentials from basic auth or challenge if no credentials
		try:
			user, pswd = get_credentials(os.environ)
		except:
			retcode = 401
		if retcode == "MATCH_ALL":
			authenticated = authenticate_gl_db(user, pswd)
		if retcode == "MATCH_USER":
			# Add check for room owner
			if check_owner(meetingid, user):
				authenticated = authenticate_gl_db(user, pswd)
		if retcode == "MATCH_SHARED":
			if check_shared(meetingid, user) or check_owner(meetingid, user):
				authenticated = authenticate_gl_db(user, pswd)
		if authenticated:
			retcode = 200
	ret_auth(retcode)
else:
	ret_auth(200)

