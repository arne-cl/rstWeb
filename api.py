#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides a REST-based API for rstWeb. Meant for local use only
(i.e. by running 'python start_local.py'), since the user 'local' is
automatically logged in and authentication is skipped.

Author: Arne Neumann
"""

from __future__ import print_function
import base64
from collections import defaultdict
import json
import os

import cherrypy

from modules.rstweb_sql import (
    create_project, delete_project, generic_query, get_all_projects, import_document)
from quick_export import quickexp_main
from screenshot import get_png


def get_all_docs(user, project):
    """Returns a list of all documents of the given user in the given project."""
    return [elem[0] for elem in generic_query("SELECT doc FROM docs WHERE user=? AND project=?", (user, project))]

def get_screenshot(file_name, project_name, user, output_format='png'):
    """Produces a screenshot of the rhetorical structure tree of a document from
    the given user in the given project and returns it.

    If `output_format` is `png`, return the image as a download (which will trigger
    the "save file" dialog on the client side.
    If `output_format` is `png-base64`, return a base64-encoded string of the png
    image.
    """
    png_bytes = get_png(file_name, project_name, user=user, mode='local')

    if output_format == 'png':
        cherrypy.response.headers['Content-Type'] = "application/download"
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{0}.png"'.format(file_name)
        return png_bytes
    elif output_format == 'png-base64':
        cherrypy.response.headers['Content-Type'] = "data:image/png;base64"
        return base64.b64encode(png_bytes)
    else:
        raise cherrypy.HTTPError(
            400, ("Unknown screenshot format '{0}'. Supported formats: png, png-base64.").format(output_format))

def get_rs3_file(file_name, project_name, user):
    """Returns a .rs3 file as a download."""
    kwargs = {'quickexp_doc': file_name, 'quickexp_project': project_name}
    cherrypy.response.headers['Content-Type'] = "application/download"
    cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(file_name)
    return quickexp_main(user=user, admin='3', mode='local', **kwargs)

def edit_document(file_name, project_name):
    """Opens a document in the rstWeb structure editor."""
    kwargs = {
        'current_doc': file_name,
        'current_guidelines': u'**current_guidelines**',
        'current_project': project_name,
        'serve_mode': u'local'
    }
    url_params = kwargs2urlparams(kwargs)
    raise cherrypy.HTTPRedirect('/structure?{0}'.format(url_params))


def kwargs2urlparams(kwargs):
    """Converts a key-value dict into a string of URL parameters. Dict entries
    with empty values will be ignored. This is used when redirecting API requests
    to existing methods of the rstWeb app.

    Example:

        >>> kwargs2urlparams({'foo': 'bar', 'ham': 'egg', 'a': ''})
        'foo=bar&ham=egg'
    """
    return '&'.join('{0}={1}'.format(k, v) for k, v in kwargs.items() if v)


class APIController(object):
    """REST API for rstWeb"""
    @cherrypy.expose
    def get_index(self):
        """Handler for / (GET)

        TODO: return a list of all available handlers (incl. paths, URL parameters and use case).
        To implement this, try this as a starting point:

            a = cherrypy.tree.apps['/api']
            r = a.config['/']['request.dispatch']
        """
        return "rstWeb API"

    @cherrypy.tools.json_out()
    def get_projects(self):
        """Handler for /projects (GET).
        Returns a list of all projects.
        """
        return {'projects': [elem[0] for elem in get_all_projects()]}

    @cherrypy.expose
    def delete_projects(self):
        """Handler for /projects (DELETE).
        Deletes all projects.
        """
        for project in self.get_projects():
            rstweb_sql.delete_project(project)

    @cherrypy.tools.json_out()
    def get_project(self, project_name):
        """Handler for /projects/{project_name} (GET).
        Returns a list of all documents in a project of the user 'local'.
        """
        return {'documents': get_all_docs('local', project_name)}

    @cherrypy.expose
    def add_project(self, project_name):
        """Handler for /projects/{project_name} (POST).
        Adds a new project to the user 'local'. (Adding a project that already
        exists has no effect.)
        """
        rstweb_sql.create_project(project_name)

    @cherrypy.expose
    def delete_project(self, project_name):
        """Handler for /projects/{project_name} (DELETE).
        Deletes a project of the user 'local'. (Deleting a non-existing
        project has no effect.)
        """
        raise NotImplementedError

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
        # only proceed if the project and file exist (for the user 'local')
        documents = self.get_project(project_name).get('documents')
        if documents is None or file_name not in documents:
            raise cherrypy.HTTPError(
                400, ("File '{0}' not available in project '{1}' for the current user. "
                      "Available files: {2}").format(file_name, project_name, documents))

        if output == 'rs3':
            return get_rs3_file(file_name, project_name, 'local')
        elif output == 'png':
            return get_screenshot(file_name, project_name, 'local', output_format='png')
        elif output == 'png-base64':
            return get_screenshot(file_name, project_name, 'local', output_format='png-base64')
        elif output == 'editor':
            edit_document(file_name, project_name)
        else:
            raise cherrypy.HTTPError(
                400, 'Unknown output format: {0}'.format(output))

    @cherrypy.expose
    def add_document(self, project_name, file_name):
        """Handler for /documents/{project_name}/{file_name} (POST)
        Adds a new document to the given project of the user 'local'.

        Adding a document to a non-existent project will create that project
        and then add the document to it.

        Adding a document under a file_name (that already exists in the given
        project for the user 'local') will also raise an error. To update
        an existing document, use the `update_document` method.
        """
        raise NotImplementedError

    @cherrypy.expose
    def update_document(self, project_name, file_name):
        """Handler for /documents/{project_name}/{file_name} (PUT)
        Updates a document in the given project of the user 'local'.

        Updating a non-existing document is the same as adding a new document.
        """
        raise NotImplementedError


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


def create_api_dispatcher():
    dispatcher = cherrypy.dispatch.RoutesDispatcher()

    # / (GET)
    dispatcher.connect(name='api',
                       route='',
                       action='get_index',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /projects (GET)
    dispatcher.connect(name='projects',
                       route='/projects',
                       action='get_projects',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /projects (DELETE)
    dispatcher.connect(name='projects',
                       route='/projects',
                       action='delete_projects',
                       controller=APIController(),
                       conditions={'method': ['DELETE']})

    # /projects/{project_name} (GET)
    #
    # Request "/projects/notfound" (GET) to test the 404 (not found) handler
    dispatcher.connect(name='projects',
                       route='/projects/{project_name}',
                       action='get_project',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /projects/{project_name} (POST)
    dispatcher.connect(name='projects',
                       route='/projects/{project_name}',
                       action='add_project',
                       controller=APIController(),
                       conditions={'method': ['POST']})

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

    # /documents/{project_name}/{file_name} (GET)
    dispatcher.connect(name='documents',
                       route='/documents/{project_name}/{file_name}',
                       action='get_document',
                       controller=APIController(),
                       conditions={'method': ['GET']})
    return dispatcher
