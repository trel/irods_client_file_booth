# iRODS File Booth

The iRODS File Booth is a *very small* web application with two jobs - to allow visitors to upload and share a file to iRODS and download an iRODS data object shared with them.

This <a href="https://cherrypy.dev/">CherryPy</a> application uses the Python iRODS Client to connect to iRODS anonmyously and execute `put` and `get` with an iRODS ticket.

<img alt="iRODS File Booth Screenshot" src="irods_file_booth.png" width="60%">

## Configuration

```
cp app.config.template app.config
vi app.config
```

The `[file_booth]` section requires updates to point to your iRODS Zone:
```
[file_booth]
#irods_host = 'host.docker.internal'
irods_host = 'irods.example.org'
irods_zone = 'tempZone'
irods_port = 1247
```

iRODS TLS/SSL settings are in the same section.

Other configuration settings can affect the layout:

```
#title = 'iRODS File Booth'
#application_name = 'irods_client_file_booth'
#custom_html_header = ''
#custom_html_footer = ''
```

The CSS can be changed by editing `app.css`.

## Building and Running with Docker Compose

Docker Compose has been configured to volume mount the local `app.config` and `app.css`.

```
docker compose up
```

Connecting to `http://localhost:8000` (by default) will open the iRODS File Booth.
