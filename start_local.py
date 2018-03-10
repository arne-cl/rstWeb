#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Script to start localhost server using cherrypy. Meant for local use only, since the user 'local'
is automatically logged in and authentication is skipped. For server installations a web server
such as Apache should be used.

Author: Amir Zeldes
Minor changes: Arne Neumann (added REST API for importing/exporting rs3 files
"""

import json
import cherrypy
import os
from tempfile import mkdtemp
from open import open_main
from structure import structure_main
from segment import segment_main
from admin import admin_main
from quick_export import quickexp_main
from cherrypy.lib import file_generator
import StringIO

from modules.rstweb_sql import (
	create_project, delete_project, get_all_projects, import_document)


class Root(object):
	def __init__(self):
		self.import_dir = mkdtemp()

	@cherrypy.expose
	def default(self,**kwargs):
		print(kwargs)
		return '<script>document.location.href="open";</script>'

	@cherrypy.expose
	def open(self,**kwargs):
		print(kwargs)
		return open_main("local","3","local",**kwargs)

	@cherrypy.expose
	def structure(self,**kwargs):
		print(kwargs)
		if "current_doc" not in kwargs:
			return '<script>document.location.href="open";</script>'
		elif "screenshot" in kwargs:
			cherrypy.response.headers['Content-Type'] = "image/png"
			cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="' + kwargs["current_doc"] + '.png"'
			return file_generator(StringIO.StringIO(structure_main("local", "3", 'local', **kwargs)))
		else:
			return structure_main("local","3",'local',**kwargs)

	@cherrypy.expose
	def segment(self,**kwargs):
		print(kwargs)
		if "current_doc" not in kwargs:
			return '<script>document.location.href="open";</script>'
		else:
			return segment_main("local","3",'local',**kwargs)

	@cherrypy.expose
	def quick_export(self,**kwargs):
		print(kwargs)
		if "quickexp_doc" not in kwargs:
			return '<script>document.location.href="open";</script>'
		else:
			cherrypy.response.headers['Content-Type'] = "application/download"
			cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="'+kwargs["quickexp_doc"]+'"'
			return quickexp_main("local","3",'local',**kwargs)

	@cherrypy.expose
	def admin(self,**kwargs):
		print(kwargs)
		return admin_main("local","3",'local',**kwargs)

	# API methods

	@cherrypy.expose
	def add_project(self, name='rst-workbench'):
		"""adds a new project to rstWeb, then returns all existing projects (JSON)

		Usage example: curl -XPOST http://127.0.0.1:8080/add_project -F name="my-project"
		"""
		create_project(name)
		return json.dumps({'projects': [elem[0] for elem in get_all_projects()]})

	@cherrypy.expose
	def import_rs3_file(self, rs3_file, project, file_name, import_dir=None):
		"""
		Usage example: curl -XPOST http://127.0.0.1:8080/import_rs3_file -F rs3_file=@source.rs3 -F project=aaa -F file_name=target.rs3
		"""
		if import_dir is None:
			import_dir = self.import_dir

		file_content = rs3_file.file.read()
		import_filepath = os.path.join(import_dir, file_name)
		with open(import_filepath, 'w') as import_file:
			import_file.write(file_content)

		error = import_document(
			os.path.join(import_dir, file_name), project, 'local')
		if error is not None:
			cherrypy.response.status = 404
			return (
				"Cannot import document into project '{0}' with "
				"filename '{1}'. Reason: '{2}'\n").format(
					project, file_name, error)
		else:
			cherrypy.response.status = 200
			return "Imported document into project '{0}' with filename '{1}'\n".format(project, file_name)

	@cherrypy.expose
	def open_rs3_file(self, file_name, project):
		"""open an rs3 file (that you have previously uploaded) in the structure editor.

		Usage example POST: curl -v -XPOST http://127.0.0.1:8080/open_rs3_file -F file_name=target.rs3 -F project=aaa
		Usage example GET: curl -XGET "http://127.0.0.1:8080/open_rs3_file?file_name=target.rs3&project=aaa"
		"""
		kwargs = {
			'current_doc': file_name,
			'current_guidelines': u'**current_guidelines**',
			'current_project': project,
			'dirty': u'',
			'logging': u'',
			'reset': u'',
			'serve_mode': u'local',
			'timestamp': u''}
		return structure_main(user='local', admin='3', mode='local', **kwargs)

	@cherrypy.expose
	def export_rs3_file(self, file_name, project):
		"""download an rs3 file from the rstWeb server.

		Note: If you have edited the rs3 file in the structure editor,
		you need to press the "save" button to update the file in the
		database first.

		Usage example GET: curl -XGET "http://127.0.0.1:8080/export_rs3_file?file_name=target.rs3&project=aaa"
		"""
		kwargs = {'quickexp_doc': file_name, 'quickexp_project': project}
		cherrypy.response.headers['Content-Type'] = "application/download"
		cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="'+kwargs["quickexp_doc"]+'"'
		return quickexp_main(user='local', admin='3', mode='local', **kwargs)


current_dir = os.path.dirname(os.path.realpath(__file__)) + os.sep
conf = {
		'/css': {'tools.staticdir.on': True,'tools.staticdir.dir': os.path.join(current_dir,'css')},
		'/img': {'tools.staticdir.on': True,'tools.staticdir.dir': os.path.join(current_dir,'img')},
		'/script': {'tools.staticdir.on': True,'tools.staticdir.dir': os.path.join(current_dir,'script')}
		}

cherrypy.quickstart(Root(), '/', conf)
