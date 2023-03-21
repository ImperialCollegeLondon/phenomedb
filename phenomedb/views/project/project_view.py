import os, sys, json, logging
from datetime import datetime
from pprint import pprint
import pandas as pd
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, make_response, redirect, url_for
#from flask_admin import BaseView, expose

from flask_appbuilder import expose, has_access
from flask.logging import default_handler

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.config import config


import phenomedb.database as db
#import phenomedb.views as dao
import phenomedb.utilities as utils
from phenomedb.models import *

from phenomedb.base_view import *

from sqlalchemy.exc import IntegrityError
# this is only Airflow specific part:
from airflow.plugins_manager import AirflowPlugin

VIEW_NAME = "project"
# log file directory is configured in config.ini

class ProjectView(PhenomeDBBaseView):

    roles = null
    selected_role=1

    def __init__(self):
        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)

  
    @expose('/')
    @has_access
    def list(self):
        self.set_db_session(request)
        self.roles=self.db_session.query(Role).order_by(Role.name)
        projects=dict()
        unallowedprojects=dict()
        for role in self.roles:
            projects[role.id] = Project.get_project_for_role(self.db_session,role.id)
            unallowedprojects[role.id] = Project.get_project_not_for_role(self.db_session,role.id)

        return self.render_template('project/project.html', projects=projects, unallowedprojects=unallowedprojects, roles=self.roles, selected_role=self.selected_role )



    @expose('/add_project', methods=['POST'])
    @has_access
    def add_project(self):
        self.set_db_session(request)
        pr=ProjectRole()
        pr.project_id=request.form['project_id']
        pr.role_id=request.form['role_id']
        self.db_session.add(pr)
        self.db_session.commit()
        self.selected_role=pr.role.id
        return self.list()

    @expose('/delete_project', methods=['POST'])
    @has_access
    def delete_project(self):
        self.set_db_session(request)
        project_id = request.form['project_id']
        role_id = request.form['role_id']
        projectrole = self.db_session.query(ProjectRole).filter(and_(ProjectRole.role_id == role_id,ProjectRole.project_id==project_id)).first()
        self.db_session.delete(projectrole)
        self.db_session.commit()
        self.selected_role = role_id
        return self.list()


project_bp = Blueprint(
    VIEW_NAME, __name__,
    template_folder='../templates',
    static_folder='../templates/static',
    static_url_path='/static/security')


v_appbuilder_view = ProjectView()
v_appbuilder_package = {"name": "Project Roles",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}


#class ProjectPlugin(AirflowPlugin):
 #   name = VIEW_NAME

  #  flask_blueprints = [project_bp]
  #  appbuilder_views = [v_appbuilder_package]
