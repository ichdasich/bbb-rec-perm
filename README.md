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

# Installation Instructions

1. Git clone the latest greenlite rec_restriction fork

`git clone -b rec_restrictions https://github.com/ichdasich/greenlight.git`

2. Compile it with docker / run it - follow the Customize install instructions from BBB page. Make sure to merge it with the newest upstream release for greenlight!

3. Git clone rec-perm
`git clone https://github.com/ichdasich/bbb-rec-perm`

4. Install fcgiwrap if it's missing
`apt-get install fcgiwrap`

5. Install bcrypt
`apt-get install python3-bcrypt`

6. Install psycopg
`apt-get install python3-psycopg2`

7. Select the right rec-perm script for your usecase:

- auth-bbb.py - Only make presentations inaccessible when set to private with vanilla BBB
- auth-passwd-bbb.py - Password authentication with vanilla BBB
- auth-passwd-scalelite.py - Password authentication with scalelite
- auth-scalelite.py - Only make presentations inaccessible when set to private with scalelite

Copy the selected file to /var/www/html/gl-auth/auth.py (and create the directories on the path)

8. Edit you postgresql password(s) to the correct ones for greenlight (in .env) and, if used, for scalelite

9. Edit your nginx configuration as follows; Adjust hostnames where necessary

```
server {  
      listen 443 ssl;  
      server_name  localhost;  
      server_name  bbb.example.com;  
  
      access_log  /var/log/nginx/bigbluebutton.access.log;  
  
      location /gl-auth/auth.py {  
                gzip off;  
                root  /var/www/html/gl-auth;  
                fastcgi_pass  unix:/var/run/fcgiwrap.socket;  
                include /etc/nginx/fastcgi_params;  
                fastcgi_param DOCUMENT_ROOT  /var/www/html/gl-auth/;  
                fastcgi_param SCRIPT_FILENAME  /var/www/html/gl-auth/auth.py;  
      }  
  
      location = /auth {  
                internal;  
                proxy_pass              https://localhost/gl-auth/auth.py;  
                proxy_pass_request_body off;  
                proxy_set_header        Content-Length "";  
                proxy_set_header        X-Original-URI $request_uri;  
      }  
  
      # Handle RTMPT (RTMP Tunneling).  Forwards requests  
      # to Red5 on port 5080  
      location ~ (/open/|/close/|/idle/|/send/|/fcs/) {  
          proxy_pass         http://127.0.0.1:5080;  
          proxy_redirect     off;  
          proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;  
  
          client_max_body_size       10m;  
          client_body_buffer_size    128k;  
  
          proxy_connect_timeout      90;  
          proxy_send_timeout         90;  
          proxy_read_timeout         90;  
  
          proxy_buffering            off;  
          keepalive_requests         1000000000;  
      }  
  
      # Handle desktop sharing tunneling.  Forwards  
      # requests to Red5 on port 5080.  
      location /deskshare {  
           proxy_pass         http://127.0.0.1:5080;  
           proxy_redirect     default;  
           proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;  
           client_max_body_size       10m;  
           client_body_buffer_size    128k;  
           proxy_connect_timeout      90;  
           proxy_send_timeout         90;  
           proxy_read_timeout         90;  
           proxy_buffer_size          4k;  
           proxy_buffers              4 32k;  
           proxy_busy_buffers_size    64k;  
           proxy_temp_file_write_size 64k;  
           include    fastcgi_params;  
       }  
  
       # BigBlueButton landing page.  
       location / {  
          root   /var/www/bigbluebutton-default;  
          index  index.html index.htm;  
          expires 1m;  
        }  
  
        # Include specific rules for record and playback  
        include /etc/bigbluebutton/nginx/*.nginx;  
  
        #error_page  404  /404.html;  
  
        # Redirect server error pages to the static page /50x.html  
        #  
        error_page   500 502 503 504  /index.html;  
        location = /index.html {  
                root   /var/www/html/bbb-rec-perm/error-page/;  
        }  
  
    ssl_certificate /etc/letsencrypt/live/bbb.example.com/fullchain.pem; # managed by Certbot  
    ssl_certificate_key /etc/letsencrypt/live/bbb.example.com/privkey.pem; # managed by Certbot  
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot  
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot  
  
location = / {  
  return 307 /b;  
}  
  
}  
  
server {  
    if ($host = bbb.example.com) {  
        return 301 https://$host$request_uri;  
    } # managed by Certbot  
  
    listen   80;  
    listen [::]:80;  
    server_name bbb.example.com;  
    server_name localhost;  
    return 404; # managed by Certbot  
  
    root /var/www/html;  
  
    location /gl-auth/auth.py {  
                gzip off;  
                root  /var/www/html/gl-auth;  
                fastcgi_pass  unix:/var/run/fcgiwrap.socket;  
                include /etc/nginx/fastcgi_params;  
                fastcgi_param DOCUMENT_ROOT  /var/www/html/gl-auth/;  
                fastcgi_param SCRIPT_FILENAME  /var/www/html/gl-auth/auth.py;  
     }  
}  
```

10. Replace nginx configuration files in /etc/bigbluebutton/nginx 

`cp bbb-rec-perm/nginx-conf/etc/bigbluebutton/nginx/* /etc/bigbluebutton/nginx`

11. In case you are using the passwordless rec-perm config, copy the custom error page to your webroot and adjust the configuration accordingly.
