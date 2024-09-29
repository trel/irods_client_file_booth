import ssl
import time
from tempfile import NamedTemporaryFile

import cherrypy
from cherrypy.lib import static

import irods.exception
import irods.keywords as kw
from irods.models import Collection, DataObject
from irods.session import iRODSSession
from irods.ticket import Ticket
from tempfile import NamedTemporaryFile


defaults = {
  'title': "iRODS File Booth",
  'application_name': 'irods_client_file_booth',
  'upload_collection_prefix': 'home/public',
  'custom_html_header': '',
  'custom_html_footer': "<p><a href='/'>Home</a> - <a href='/test'>test</a></p>",
  'ticket_uses_limit': 3,
  'ticket_expiry_in_seconds': 3600
}

def merge_custom_into_default_config(config):
    defaults.update(config)
    return defaults

def get_header(config):
    h = '''\
<html>
    <head>
    <title>{}</title>
    <link rel="stylesheet" href="app.css">
    </head>
    <body>
'''.format(config['title'])
    return h + config['custom_html_header']

def get_footer(config):
    f = '''\
    </body>
</html>
'''
    return config['custom_html_footer'] + f

def get_ssl_settings(config):
    ssl_settings = {'client_server_negotiation': config['client_server_negotiation'],
                    'client_server_policy': config['client_server_policy'],
                    'encryption_algorithm': config['encryption_algorithm'],
                    'encryption_key_size': config['encryption_key_size'],
                    'encryption_num_hash_rounds': config['encryption_num_hash_rounds'],
                    'encryption_salt_size': config['encryption_salt_size'],
                    'ssl_verify_server': config['ssl_verify_server'],
                    'ssl_ca_certificate_file': config['ssl_ca_certificate_file']
    }
    return ssl_settings

class Root(object):

    @cherrypy.expose
    def test(self):
        config = merge_custom_into_default_config(cherrypy.request.app.config['file_booth'])
        html_header = get_header(config)
        html_footer = get_footer(config)
        ssl_settings = get_ssl_settings(config)
        with iRODSSession(  host=config['irods_host'],
                            port=config['irods_port'],
                            zone=config['irods_zone'],
                            user='alice',
                            password='apass',
                            application_name=config['application_name'],
                            **ssl_settings) as session:
            try:
                html_body = ""
                html_body += '<br/>config [{}]'.format(config)
                html_body += '<br/>session.pool.application_name [{}]'.format(session.pool.application_name)
                html_body += '<br/>session.server_version [{}]'.format(session.server_version)
                connections = session.pool.active | session.pool.idle
                html_body += '<br/>len(connections) [{}]'.format(len(connections))
                is_SSL = len(connections) > 0 and all(isinstance(conn.socket, ssl.SSLSocket) for conn in connections)
                html_body += '<br/>is_SSL [{}]'.format(is_SSL)
                html_body += '<br/>session.host [{}]'.format(session.host)
                html_body += '<br/>session.zone [{}]'.format(session.zone)
                html_body += '<br/>session.port [{}]'.format(session.port)
                html_body += '<br/>session.numThreads [{}]'.format(session.numThreads)
                home_collection = "/{}/home/{}".format(session.zone, session.username)
                html_body += '<br/><br/>home_collection [{}]'.format(home_collection)
                h = session.collections.get(home_collection)
                html_body += "<br/>- id[{}] path[{}] ctime[{}] mtime[{}]".format(h.id, h.path, h.create_time, h.modify_time)
                html_body += "<br/><br/>subcollections"
                for c in h.subcollections:
                    html_body += "<br/>- id[{}] path[{}] ctime[{}] mtime[{}]".format(c.id, c.path, c.create_time, c.modify_time)
                html_body += "<br/><br/>data_objects"
                for d in h.data_objects:
                    html_body += "<br/>- id[{}] name[{}] ctime[{}] mtime[{}]".format(d.id, d.name, d.create_time, d.modify_time)
                return html_header + html_body + html_footer
            except Exception as e:
                html_body = repr(e)
                return html_header + html_body + html_footer

    @cherrypy.expose
    def index(self):
        config = merge_custom_into_default_config(cherrypy.request.app.config['file_booth'])
        html_header = get_header(config)
        html_footer = get_footer(config)
        html_body = '''\
        <table border=0 align=center>
        <tr>
           <form method="post" action="upload" enctype="multipart/form-data">
           <td><input type="file" name="filename"/></td>
           <td><button class="button" type="submit">Upload</button></td>
           </form>
        </tr>
        <tr>
           <form method="post" action="download">
           <td><input type="text" id="t" name="t"/></td>
           <td><button class="button" type="submit">Download</button></td>
           </form>
        </tr>
        </table>
        '''
        return html_header + html_body + html_footer

    @cherrypy.expose
    def download(self, *args, **kwargs):
        config = merge_custom_into_default_config(cherrypy.request.app.config['file_booth'])
        html_header = get_header(config)
        html_footer = get_footer(config)
        # arguments
        ticket_string = kwargs.get('t')

        # build session
        ssl_settings = get_ssl_settings(config)
        with iRODSSession(  host=config['irods_host'],
                            port=config['irods_port'],
                            zone=config['irods_zone'],
                            user='anonymous',
                            password='',
                            application_name=config['application_name'],
                            **ssl_settings) as session:
            try:
                # apply supplied ticket
                Ticket(session, ticket_string).supply()
                # query for the data object information
                result = session.query(Collection.name, DataObject.name).one()
                # build logical_path
                logical_path = ( result[Collection.name] + '/' + result[DataObject.name] )
                # use temporary file
                with NamedTemporaryFile(delete_on_close=False) as tf:
                    # get iRODS file to temporary file
                    options = {}
                    options["allow_redirect"] = False
                    options[kw.FORCE_FLAG_KW] = ""
                    session.data_objects.get(logical_path, tf.name, **options)
                    # serve static file as attachment to browser
                    return static.serve_file(tf.name,
                                             'application/x-download',
                                             'attachment',
                                             result[DataObject.name])
            except Exception as e:
                html_body = repr(e)
                return html_header + html_body + html_footer

    #https://stackoverflow.com/a/38998044
    @cherrypy.expose
    def upload(self, filename):
        if cherrypy.request.method != 'POST':
            return 'only POST supported'
        config = merge_custom_into_default_config(cherrypy.request.app.config['file_booth'])
        html_header = get_header(config)
        html_footer = get_footer(config)
        # arguments
        uploaded_file = filename

        # build session
        ssl_settings = get_ssl_settings(config)
        with iRODSSession(  host=config['irods_host'],
                            port=config['irods_port'],
                            zone=config['irods_zone'],
                            user='anonymous',
                            password='',
                            application_name=config['application_name'],
                            **ssl_settings) as session:
            try:
                logical_path = '/{0.zone}/{1}/{2}'.format(session, config['upload_collection_prefix'].lstrip('/'), uploaded_file.filename)
                size = 0
                options = {}
                options["allow_redirect"] = False
                with session.data_objects.open(logical_path,"w", **options) as f:
                    while True:
                        data = uploaded_file.file.read(8192)
                        if not data:
                            break
                        f.write(data)
                        size += len(data)

                new_ticket = Ticket(session)
                new_ticket.issue('read', logical_path)
                new_ticket.modify('uses', int(config['ticket_uses_limit']))
                new_ticket.modify('expire', int( time.time() + int(config['ticket_expiry_in_seconds'])))
                html_body = 'Your file is available at: {0}/download?t={1}'.format(cherrypy.request.base, new_ticket.string)
                return html_header + html_body + html_footer
            except Exception as e:
                html_body = repr(e)
                return html_header + html_body + html_footer

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', 'app.config')
