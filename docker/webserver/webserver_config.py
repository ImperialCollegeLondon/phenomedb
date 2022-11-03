
import os
from flask_appbuilder.security.manager import AUTH_LDAP,AUTH_DB

basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = os.environ.get('AIRFLOW__CORE__SQL_ALCHEMY_CONN')
CSRF_ENABLED = True

AUTH_TYPE = AUTH_DB

#AUTH_TYPE = AUTH_LDAP
#AUTH_ROLE_ADMIN = 'Admin'
##AUTH_USER_REGISTRATION = True
#AUTH_USER_REGISTRATION_ROLE = 'Admin'
#AUTH_LDAP_SERVER = 'ldap://unixldap.cc.ic.ac.uk'
#AUTH_LDAP_SEARCH = 'ou=People,ou=everyone,DC=ic,DC=ac,DC=uk'
#AUTH_LDAP_USERNAME_FORMAT = 'uid=%s,ou=People,ou=everyone,dc=ic,dc=ac,dc=uk'
#AUTH_LDAP_FIRSTNAME_FIELD = 'givenName'
#AUTH_LDAP_LASTNAME_FIELD = 'sn'