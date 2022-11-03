import sys
import logging
import os

if os.environ['PHENOMEDB_PATH'] not in sys.path:
   sys.path.append(  os.environ['PHENOMEDB_PATH'])
# PhenomeDB imports

from flask import request
from flask_appbuilder.api import BaseApi, expose, rison, safe
from flask_appbuilder.security.decorators import protect
from flask_login import current_user,confirm_login
from . import appbuilder

import phenomedb.database as db
from phenomedb.models import *
from phenomedb.config import config
from phenomedb.query_factory import *


API_NAME = "saved_query"

class SavedQuery(BaseApi):

    def __init__(self):

        super().__init__()
        self.configure_logging(identifier=API_NAME)
        # all fields for table:

    def configure_logging(self,identifier='saved_query', log_file='api.log', level=logging.INFO):
        '''
        to set up a logger
        :param identifier: an identifier for your messages in the log
        :param log_file: file to log to at location specified in config.ini; (will create this dir if nec).
        :param logging level DEBUG by default
        '''
        self.logger = None
        try:

            self.logger = logging.getLogger(identifier)

            log_dir =  config['LOGGING']['dir']
            log_file = os.path.join(log_dir, log_file)

            os.makedirs(log_dir, exist_ok=True)
            fh = logging.FileHandler(log_file, mode="a", encoding="utf-8", delay=False)

            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
            fh.setFormatter(formatter)

            self.logger.addHandler(fh)
            self.logger.setLevel(level)
            #print("Initialised " + identifier + " to log to", log_file)
        except OSError as e:
            print('Error configuring logging', e)

    @expose("/getsummary",methods=['GET'])
    @protect()
    def getsummary(self):
        """Get query summary stats
        ---
        get:
          summary: Get SavedQuery summary stats
          parameters:
            - in: query
              name: name
              schema:
                type: string
              required: false
              description: The name of the saved query
            - in: query
              name: id
              schema:
                type: integer
              required: false
              description: The id of the saved query
            - in: query
              name: db_env
              schema:
                type: string
              required: false
              description: The db_env to use, "TEST", "BETA", or default "PROD"

          responses:
            200:
              description: The summary statistics of the query
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      saved_query:
                        type: object
                      summary_statistics:
                        type: object
        """

        if 'name' in request.args \
            or 'id' in request.args:

            try:
                if 'db_env' in request.args:
                    db_env = request.args.get('db_env')
                else:
                    db_env = 'PROD'

                db_session = db.get_db_session(db_env=db_env)

                if 'id' in request.args:

                    field = SavedQuery.id
                    value = request.args.get('id').strip()

                elif 'name' in request.args:
                    field = SavedQuery.name
                    value = request.args.get('name').strip()

                saved_query = db_session.query(SavedQuery).filter(field==value).first()

                factory = None

                if not saved_query:
                    raise Exception("Unknown SavedQuery")

                query_factory = QueryFactory(saved_query=saved_query)


                summary_statistics = query_factory.load_summary_statistics()

                return self.response(200, saved_query=saved_query, summary_statistics=summary_statistics)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')


    @expose("/getresults",methods=['GET'])
    @protect()
    def getresults(self):
        """Get query results
        ---
        get:
          summary: Get SavedQuery result rows
          parameters:
            - in: query
              name: name
              schema:
                type: string
              required: false
              description: The name of the saved query
            - in: query
              name: id
              schema:
                type: integer
              required: false
              description: The id of the saved query
            - in: query
              name: limit
              schema:
                type: integer
              required: false
              description: The limit of number of rows to return, for pagination purposes
            - in: query
              name: offset
              schema:
                type: integer
              required: false
              description: The offset of rows to return, for pagination purposes
            - in: query
              name: db_env
              schema:
                type: string
              required: false
              description: The db_env to use, "TEST", "BETA", or default "PROD"

          responses:
            200:
              description: The summary statistics of the query
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      saved_query:
                        type: object
                      results:
                        type: object
        """

        if 'name' in request.args \
                or 'id' in request.args:

            try:
                if 'db_env' in request.args:
                    db_env = request.args.get('db_env')
                else:
                    db_env = 'PROD'

                db_session = db.get_db_session(db_env=db_env)

                if 'id' in request.args:

                    field = SavedQuery.id
                    value = request.args.get('id').strip()

                elif 'name' in request.args:
                    field = SavedQuery.name
                    value = request.args.get('name').strip()

                saved_query = db_session.query(SavedQuery).filter(field==value).first()

                if not saved_query:
                    raise Exception("Unknown SavedQuery")

                query_factory = QueryFactory(saved_query=saved_query)

                if 'limit' in request.args:
                    limit = int(request.args['limit'])
                else:
                    limit = None

                if 'offset' in request.args:
                    offset = int(request.args['offset'])
                else:
                    offset = None

                results = query_factory.execute_query(limit=limit,offset=offset)

                return self.response(200, saved_query=saved_query, results=results)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')

    @expose("/getdataframe",methods=['GET'])
    @protect()
    def getdataframe(self):
        """Get query results as dataframe
        ---
        get:
          summary: Get SavedQuery QueryFactory dataframe result rows
          parameters:
            - in: query
              name: name
              schema:
                type: string
              required: false
              description: The name of the saved query
            - in: query
              name: id
              schema:
                type: integer
              required: false
              description: The id of the saved query
            - in: query
              name: db_env
              schema:
                type: string
              required: false
              description: The db_env to use, "TEST", "BETA", or default "PROD"

          responses:
            200:
              description: The summary statistics of the query
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      saved_query:
                        type: object
                      results:
                        type: object
        """

        if 'name' in request.args \
                or 'id' in request.args:

            try:
                if 'db_env' in request.args:
                    db_env = request.args.get('db_env')
                else:
                    db_env = 'PROD'

                db_session = db.get_db_session(db_env=db_env)

                if 'id' in request.args:

                    field = SavedQuery.id
                    value = request.args.get('id').strip()

                elif 'name' in request.args:
                    field = SavedQuery.name
                    value = request.args.get('name').strip()

                saved_query = db_session.query(SavedQuery).filter(field==value).first()

                query_factory = None


                query_factory = QueryFactory(saved_query=saved_query)

                dataframe = query_factory.load_dataframe()

                return self.response(200, saved_query=saved_query, dataframe=dataframe)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')

    @expose("/getintensitysamplefeaturemetadata",methods=['GET'])
    @protect()
    def getintensitysamplefeaturemetadata(self):
        """Get intensity matrix, sample metadata dataframe and feature metadata dataframe
        ---
        get:
          summary: Get intensity matrix, sample metadata dataframe and feature metadata dataframe
          parameters:
            - in: query
              name: name
              schema:
                type: string
              required: false
              description: The name of the saved query
            - in: query
              name: id
              schema:
                type: integer
              required: false
              description: The id of the saved query
            - in: query
              name: db_env
              schema:
                type: string
              required: false
              description: The db_env to use, "TEST", "BETA", or default "PROD"

          responses:
            200:
              description: The summary statistics of the query
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      saved_query:
                        type: phenomedb.models.SavedQuery
                      xmatrix:
                        type: numpy.ndarray
                      sample_metadata:
                        type: pandas.Dataframe
                      feature_metadata:
                        type: pandas.Dataframe
        """

        if 'name' in request.args \
                or 'id' in request.args:

            try:
                if 'db_env' in request.args:
                    db_env = request.args.get('db_env')
                else:
                    db_env = 'PROD'

                db_session = db.get_db_session(db_env=db_env)

                if 'id' in request.args:

                    field = SavedQuery.id
                    value = request.args.get('id').strip()

                elif 'name' in request.args:
                    field = SavedQuery.name
                    value = request.args.get('name').strip()

                saved_query = db_session.query(SavedQuery).filter(field==value).first()

                query_factory = None

                if not saved_query:
                    raise Exception("Unknown SavedQuery")

                query_factory = QueryFactory(saved_query=saved_query)

                dataframe = query_factory.load_dataframe()
                query_factory.build_intensity_data_sample_metadata_and_feature_metadata()

                return self.response(200, saved_query=saved_query,
                                        xmatrix=query_factory.intensity_data,
                                        sample_metadata=query_factory.sample_metadata,
                                        feature_metadata=query_factory.feature_metadata)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')



appbuilder.add_api(SavedQuery)


