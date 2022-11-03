


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from airflow.configuration import conf

airflow_database_connection_string = conf.get('CORE','sql_alchemy_conn')
airflow_engine = create_engine(airflow_database_connection_string, echo=False)
airflow_Session = sessionmaker(bind=airflow_engine,autocommit=False)

def get_airflow_db_session():
    """Get the db session from airflow - used for Airflow Pipelines

    :return: The SQL Alchemy Session
    :rtype: `sqlalchemy.orm.Session`
    """    

    return airflow_Session()