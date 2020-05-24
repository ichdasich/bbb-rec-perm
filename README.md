# Finer access to BigBlueButton recordings with greenlight
This toolchain allows restricting access to unlisted / not intended for
publications on a BigBlueButton server with a greenlight frontend. (Related to
https://github.com/bigbluebutton/bigbluebutton/issues/8505 and 
https://github.com/bigbluebutton/bigbluebutton/issues/8870).

## Architecture 

We use the request-auth feature of nginx. When a resource connected to the
recordings is accessed, we trigger an internal auth request to a CGI script
also running on localhost.  This script then checks the scalelite DB (if it is
used) or local recording metadata to find the gl-listed property.  If this is
set to false (default of greenlight for unlisted recordings, i.e., recordings
that are not listed in greenlight but still accessible directly via BBB. If it
is set to true or any other value, the recording becomes accessible.

Access to thumbnails and favicons is always granted to ensure proper
presentation in the GL frontend, even if the gl-listed value is set to false,
rendering the recording inaccessible. 

## Greenlight integration

To make permissions more fine-grained, I added a third value to gl-listed
(initially only true/false). Now it can also be set to unlisted, with the
following semantics:

- Private/false: Recording is not accessible
- Unlisted/unlisted: Recording is accessible but not listed in the greenlight 
  room overview (As with Unlisted/false before)
- Public/true: Recording is accessible and listed on the room page

The greenlight integration is available at: https://github.com/ichdasich/greenlight/tree/rec_restrictions 

## Custom error page

In addition, you can also use the error page (with far too much css overhead)
supplied in error-page/ (placed into the directory /bbb relative to your
webroot in the supplied nginx conf) to display an error page that explains
these settings to your users, in case you also use the greenlight integration.

### Password authentication for recordings

The password authentication auth-hooks add the ability to use `HTTP_AUTH`
against the greenlight user database. For this to work, python3-bcrypt must be
installed as well.  The scripts allow you to configure the gllisted values that
trigger the following auth cases:

#### `PUBLIC`
The meeting is publicly available, i.e., accessible without authentication.

#### `GL_AUTH`
Any credentials of any GL user work.

#### `GL_USER_PRIV`
Only the credentials of the room owner work.

#### `GL_USER_SHARE`
Credentials of the room owner and anyone they shared the room with work.
