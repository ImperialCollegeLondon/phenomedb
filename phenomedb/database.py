import numpy as np
from psycopg2.extensions import register_adapter, AsIs
register_adapter(np.int64, AsIs)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,scoped_session
import os
from phenomedb.config import config

test_database = config['DB']['test']

prod_database_connection_string = config['DB']['rdbms'] + '://' + config['DB']['user'] + ':' +  config['DB']['password'] + '@' +  config['DB']['host'] + ':' +  config['DB']['port'] + '/' +  config['DB']['name']
test_database_connection_string = config['DB']['rdbms'] + '://' + config['DB']['user'] + ':' +  config['DB']['password'] + '@' +  config['DB']['host'] + ':' +  config['DB']['port'] + '/' +  config['DB']['test']
beta_database_connection_string = config['DB']['rdbms'] + '://' + config['DB']['user'] + ':' +  config['DB']['password'] + '@' +  config['DB']['host'] + ':' +  config['DB']['port'] + '/' +  config['DB']['beta']

# adding these as constants because I mis-type so much
DB_TEST = "TEST"
DB_PROD = "PROD"
DB_BETA = "BETA"

prod_engine = create_engine(prod_database_connection_string, echo=False,pool_size=int(float(config['DB']['pool_size'])), max_overflow=int(float(config['DB']['max_overflow'])))
test_engine = create_engine(test_database_connection_string, echo=False,pool_size=int(float(config['DB']['pool_size'])), max_overflow=int(float(config['DB']['max_overflow'])))
beta_engine = create_engine(beta_database_connection_string, echo=False,pool_size=int(float(config['DB']['pool_size'])), max_overflow=int(float(config['DB']['max_overflow'])))

# 1. create the engines and sessions for each environment at the beginning
# 2. get the correct session based on the db_env specified

# Create the engine the connection pool will use
#engine = create_engine(database_connection_string, echo=False)

# Create the session object to be used by all entities
Prod_Session = scoped_session(sessionmaker(bind=prod_engine,autocommit=False))
Test_Session = scoped_session(sessionmaker(bind=test_engine,autocommit=False))
Beta_Session = scoped_session(sessionmaker(bind=beta_engine,autocommit=False))

def get_database_session():
    """Get a production database session.

    :return: production database session.
    :rtype: :class:`sqlalchemy.orm.Session`
    """    
    session = Prod_Session()
    print("Getting PROD DB session", session.bind)
    return session


def get_test_database_session():
    """Get a test database session.

    :return: test database session.
    :rtype: :class:`sqlalchemy.orm.Session`
    """    
    session = Test_Session()
    print("Getting TEST session", session.bind)
    
    return session


def get_beta_database_session():
    """Get a beta database session.

    :return: beta database session.
    :rtype: :class:`sqlalchemy.orm.Session`
    """    
    session = Beta_Session()
    print("Getting BETA session", session.bind)
    return session

def get_db_session(db_env=None):
    """Get a db_session

    :param db_env: 'PROD', 'BETA', 'TEST', defaults to None (PROD).
    :type db_env: str, optional
    :return: The database session.
    :rtype: :class:`sqlalchemy.orm.Session`
    """    

    # the test_session will be set from the test_views module only
    if db_env == DB_TEST:
        return get_test_database_session()

    elif db_env == DB_BETA:
        return get_beta_database_session()

    else:
        return get_database_session()

