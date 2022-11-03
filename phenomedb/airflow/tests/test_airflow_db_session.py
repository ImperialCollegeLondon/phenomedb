import pytest

import sys, os
if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

import phenomedb.airflow.database as db

class TestAirflowDBSession:

    def test_a_get_session(self):

        airflow_session = db.get_airflow_db_session()

        print(airflow_session)
