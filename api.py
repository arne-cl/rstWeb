#!/usr/bin/env python

# pylint: disable=invalid-name

"""
CherryPy-based webservice daemon with background threads
"""

from __future__ import print_function
from collections import defaultdict
import threading
import json
import os

import cherrypy
from cherrypy.lib import auth_basic  # noqa pylint: disable=unused-import
from cherrypy.process import plugins
import cherrypy_cors

from modules.rstweb_sql import (
    create_project, delete_project, generic_query, get_all_projects, import_document)
from quick_export import quickexp_main
from screenshot import get_png
from structure import structure_main

sample_nodes = [
    'node1',
    'node2',
]

#def get_users(doc,project):
#	return generic_query("SELECT user from rst_nodes WHERE doc=? and project=? and not user='_orig'",(doc,project))


def get_all_docs(user, project):
    return [elem[0] for elem in generic_query("SELECT doc FROM docs WHERE user=? AND project=?", (user, project))]


class APIController(object):
    @cherrypy.tools.json_out()
    def get_projects(self):
        """Handler for /projects (GET).
        Returns a list of all projects.
        """
        return {'projects': [elem[0] for elem in get_all_projects()]}

    @cherrypy.tools.json_out()
    def get_project(self, project_name):
        """Handler for /projects/{project_name} (GET).
        Returns a list of all documents in a project of the user 'local'.
        """
        return {'documents': get_all_docs('local', project_name)}

    @cherrypy.tools.json_out()
    def get_documents(self):
        """Handler for /documents (GET).
        Returns a JSON struct containing all documents in all projects of the
        user 'local'.
        """
        all_documents = generic_query("SELECT doc, project FROM docs WHERE user=?", ('local',))
        docs_dict = defaultdict(list)
        for file_name, project_name in all_documents:
            docs_dict[project_name].append(file_name)
        return {'documents': docs_dict}

    @cherrypy.expose
    def get_document(self, project_name, file_name, output='rs3'):
        """Handler for /documents/{project_name}/{file_name} (GET)
        TODO: how to get URL params: ?output={rs3, png, png-base64, editor}"""
        # only proceed if file exists (in this project, for this user)
        documents = self.get_project(project_name)['documents']
        if file_name not in documents:
            raise cherrypy.HTTPError(
                400, ("File '{0}' not available in project '{1}' for the current user. "
                      "Available files: {2}").format(file_name, project_name, documents))

        if output == 'rs3':
            # download the .rs3 file
            kwargs = {'quickexp_doc': file_name, 'quickexp_project': project_name}
            cherrypy.response.headers['Content-Type'] = "application/download"
            cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(file_name)
            return quickexp_main(user='local', admin='3', mode='local', **kwargs)
        elif output == 'png':
                # "download a .png image of a rhetorical structure tree of an rs3 file
                # that is already stored in the given project.
            cherrypy.response.headers['Content-Type'] = "application/download"
            cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{0}.png"'.format(file_name)
            return get_png(file_name, project_name, user='local', mode='local')
        elif output == 'png-base64':
            raise NotImplementedError
        elif output == 'editor':
            kwargs = {
                'current_doc': file_name,
                'current_guidelines': u'**current_guidelines**',
                'current_project': project_name,
                'dirty': u'',
                'logging': u'',
                'reset': u'',
                'serve_mode': u'local',
                'timestamp': u''}
            return structure_main(user='local', admin='3', mode='local', **kwargs)
        else:
            raise cherrypy.HTTPError(
                400, 'Unknown output format: {0}'.format(output))
            
#        import pudb; pudb.set_trace()

    """Controller for fictional "nodes" webservice APIs"""

    @cherrypy.tools.json_out()
    def get_all(self): \
            # pylint: disable=no-self-use
        """
        Handler for /nodes (GET)
        """
        return [{'name': name} for name in sample_nodes]

    @cherrypy.tools.json_out()
    def get(self, name): \
            # pylint: disable=no-self-use
        """
        Handler for /nodes/<name> (GET)
        """

        if name not in sample_nodes:
            raise cherrypy.HTTPError(
                404, 'Node \"{0}\" not found'.format(name))

        return [{'name': name}]

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def add_node(self): \
            # pylint: disable=no-self-use
        """
        Handler for /nodes (POST)
        """

        request_data = cherrypy.request.json

        data, errors = NodeSchema().load(request_data)

        if errors:
            # Attempt to format errors dict from Marshmallow
            errmsg = ', '.join(
                ['Key: [{0}], Error: {1}'.format(key, error)
                 for key, error in errors.items()])

            raise cherrypy.HTTPError(
                400, 'Malformed POST request data: {0}'.format(errmsg))

        # Successful POST request
        return 'TODO: add node [{0}]'.format(data['name'])

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def update_node(self, name): \
            # pylint: disable=no-self-use
        """
        Handler for /nodes/<name> (PUT)
        """

        if name not in sample_nodes:
            raise cherrypy.HTTPError(
                404, 'Node \"{0}\" not found'.format(name))

        # Empty response (http status 204) for successful PUT request
        cherrypy.response.status = 204

        return ''

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def delete_node(self, name): \
            # pylint: disable=unused-argument,no-self-use
        """
        Handler for /nodes/<name> (DELETE)
        """

        # TODO: handle DELETE here

        # Empty response (http status 204) for successful DELETE request
        cherrypy.response.status = 204

        return ''


def jsonify_error(status, message, traceback, version): \
        # pylint: disable=unused-argument

    """JSONify all CherryPy error responses (created by raising the
    cherrypy.HTTPError exception)
    """

    cherrypy.response.headers['Content-Type'] = 'application/json'
    response_body = json.dumps(
        {
            'error': {
                'http_status': status,
                'message': message,
            }
        })

    cherrypy.response.status = status

    return response_body


def validate_password(realm, username, password): \
        # pylint: disable=unused-argument
    """
    Simple password validation
    """
    return username in USERS and USERS[username] == password


if __name__ == '__main__':
    cherrypy_cors.install()

    dispatcher = cherrypy.dispatch.RoutesDispatcher()

    # /projects (GET)
    dispatcher.connect(name='projects',
                       route='/projects',
                       action='get_projects',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /projects/{project_name} (GET)
    #
    # Request "/projects/notfound" (GET) to test the 404 (not found) handler
    dispatcher.connect(name='projects',
                       route='/projects/{project_name}',
                       action='get_project',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /documents (GET)
    dispatcher.connect(name='documents',
                       route='/documents',
                       action='get_documents',
                       controller=APIController(),
                       conditions={'method': ['GET']})


    # /documents/{project_name} (GET)
    #
    # Request "/projects/notfound" (GET) to test the 404 (not found) handler
    #
    # Right now, /projects/{project_name} and /documents/{project_name} both use get_project().
    # This might change if we want to show more info on a project than just its file names.
    dispatcher.connect(name='documents',
                       route='/documents/{project_name}',
                       action='get_project',
                       controller=APIController(),
                       conditions={'method': ['GET']})


    # ~ def get_document(self, project_name, file_name, output):

    # /documents/{project_name}/{file_name} (GET)
    dispatcher.connect(name='documents',
                       route='/documents/{project_name}/{file_name}',
                       action='get_document',
                       controller=APIController(),
                       conditions={'method': ['GET']})


    # /nodes (GET)
    dispatcher.connect(name='nodes',
                       route='/nodes',
                       action='get_all',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /nodes/{name} (GET)
    #
    # Request "/nodes/notfound" (GET) to test the 404 (not found) handler
    dispatcher.connect(name='nodes',
                       route='/nodes/{name}',
                       action='get',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /nodes/{name} (POST)
    dispatcher.connect(name='nodes',
                       route='/nodes',
                       action='add_node',
                       controller=APIController(),
                       conditions={'method': ['POST']})

    # /nodes/{name} (PUT)
    dispatcher.connect(name='nodes',
                       route='/nodes/{name}',
                       action='update_node',
                       controller=APIController(),
                       conditions={'method': ['PUT']})

    # /nodes/{name} (DELETE)
    dispatcher.connect(name='nodes',
                       route='/nodes/{name}',
                       action='delete_node',
                       controller=APIController(),
                       conditions={'method': ['DELETE']})


    current_dir = os.path.dirname(os.path.realpath(__file__)) + os.sep

    config = {
        '/': {
            'request.dispatch': dispatcher,
            'error_page.default': jsonify_error,
            'cors.expose.on': True,
#            'tools.auth_basic.on': True,
#            'tools.auth_basic.realm': 'localhost',
#            'tools.auth_basic.checkpassword': validate_password,
        },
        '/css': {'tools.staticdir.on': True,'tools.staticdir.dir': os.path.join(current_dir,'css')},
        '/img': {'tools.staticdir.on': True,'tools.staticdir.dir': os.path.join(current_dir,'img')},
        '/script': {'tools.staticdir.on': True,'tools.staticdir.dir': os.path.join(current_dir,'script')}
    }

    cherrypy.tree.mount(root=None, config=config)

    cherrypy.config.update({
        # 'server.socket_host': '0.0.0.0',
        # 'server.socket_port': 8080,
    })

    cherrypy.engine.start()
    cherrypy.engine.block()
