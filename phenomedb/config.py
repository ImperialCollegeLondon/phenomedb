import configparser, os

config = configparser.ConfigParser()

# Either manually create a config.ini file in the data/config/ directory
# OR set the path in PHENOMEDB_CONFIG
# OR use the default data/config/default-config.py

default_config_overide_file = os.path.join(os.path.dirname(__file__), "./data/config/config.ini")

if 'PHENOMEDB_CONFIG' in os.environ:
     config_file = os.environ['PHENOMEDB_CONFIG']
elif os.path.exists(default_config_overide_file):
     config_file = default_config_overide_file
else:
     config_file = os.path.join(os.path.dirname(__file__), "./data/config/default-config.ini")

config.read(config_file)
print(config.sections())

# Credentials can be overwritten by environment variables

if 'PHENOMEDB__TEST__USERNAME' in os.environ:
     config['TEST']['username'] = os.environ['PHENOMEDB__TEST__USERNAME']

if 'PHENOMEDB__SMTP__ENABLED' in os.environ:
     config['SMTP']['enabled'] = os.environ['PHENOMEDB__SMTP__ENABLED']

if 'PHENOMEDB__SMTP__HOST' in os.environ:
     config['SMTP']['host'] = os.environ['PHENOMEDB__SMTP__HOST']

if 'PHENOMEDB__SMTP__PORT' in os.environ:
     config['SMTP']['port'] = os.environ['PHENOMEDB__SMTP__PORT']

if 'PHENOMEDB__SMTP__USER' in os.environ:
     config['SMTP']['user'] = os.environ['PHENOMEDB__SMTP__USER']

if 'PHENOMEDB__SMTP__PASSWORD' in os.environ:
     config['SMTP']['password'] = os.environ['PHENOMEDB__SMTP__PASSWORD']

if 'PHENOMEDB__SMTP__FROM' in os.environ:
     config['SMTP']['from'] = os.environ['PHENOMEDB__SMTP__FROM']

if 'PHENOMEDB__REDIS__PORT' in os.environ:
     config['REDIS']['port'] = os.environ['PHENOMEDB__REDIS__PORT']

if 'PHENOMEDB__REDIS__USER' in os.environ:
     config['REDIS']['user'] = os.environ['PHENOMEDB__REDIS__USER']

if 'PHENOMEDB__REDIS__PASSWORD' in os.environ:
     config['REDIS']['password'] = os.environ['PHENOMEDB__REDIS__PASSWORD']

if 'PHENOMEDB__REDIS__HOST' in os.environ:
     config['REDIS']['host'] = os.environ['PHENOMEDB__REDIS__HOST']

if 'PHENOMEDB__REDIS__MEMORY_EXPIRED_SECONDS' in os.environ:
     config['REDIS']['memory_expired_seconds'] = os.environ['PHENOMEDB__REDIS__MEMORY_EXPIRED_SECONDS']

if 'PHENOMEDB__REDIS__DISK_EXPIRED_SECONDS' in os.environ:
     config['REDIS']['disk_expired_seconds'] = os.environ['PHENOMEDB__REDIS__DISK_EXPIRED_SECONDS']

if 'PHENOMEDB__WEBSERVER__URL' in os.environ:
     config['WEBSERVER']['url'] = os.environ['PHENOMEDB__WEBSERVER__URL']

if 'PHENOMEDB__API__CUSTOM_ROOT' in os.environ:
     config['API']['custom_root'] = os.environ['PHENOMEDB__API__CUSTOM_ROOT']

if 'PHENOMEDB__DB__DIR' in os.environ:
     config['DB']['dir'] = os.environ['PHENOMEDB__DB__DIR']

if 'PHENOMEDB__DB__RDBMS' in os.environ:
     config['DB']['rdbms'] = os.environ['PHENOMEDB__DB__RDBMS']

if 'PHENOMEDB__DB__USER' in os.environ:
     config['DB']['user'] = os.environ['PHENOMEDB__DB__USER']

if 'PHENOMEDB__DB__PASSWORD' in os.environ:
     config['DB']['password'] = os.environ['PHENOMEDB__DB__PASSWORD']

if 'PHENOMEDB__DB__NAME' in os.environ:
     config['DB']['name'] = os.environ['PHENOMEDB__DB__NAME']

if 'PHENOMEDB__DB__HOST' in os.environ:
     config['DB']['host'] = os.environ['PHENOMEDB__DB__HOST']

if 'PHENOMEDB__DB__PORT' in os.environ:
     config['DB']['port'] = os.environ['PHENOMEDB__DB__PORT']

if 'PHENOMEDB__DB__POOL_SIZE' in os.environ:
     config['DB']['pool_size'] = os.environ['PHENOMEDB__DB__POOL_SIZE']

if 'PHENOMEDB__DB__MAX_OVERFLOW' in os.environ:
     config['DB']['max_overflow'] = os.environ['PHENOMEDB__DB__MAX_OVERFLOW']

if 'PHENOMEDB__DB__TEST' in os.environ:
     config['DB']['test'] = os.environ['PHENOMEDB__DB__TEST']

if 'PHENOMEDB__DB__BETA' in os.environ:
     config['DB']['beta'] = os.environ['PHENOMEDB__DB__BETA']

if 'PHENOMEDB__DB__CREATE_SCRIPT' in os.environ:
     config['DB']['create_script'] = os.environ['PHENOMEDB__DB__CREATE_SCRIPT']

if 'PHENOMEDB__DB__STATIC_DATA' in os.environ:
     config['DB']['static_data'] = os.environ['PHENOMEDB__DB__STATIC_DATA']

if 'PHENOMEDB__LOGGING__DIR' in os.environ:
     config['LOGGING']['dir'] = os.environ['PHENOMEDB__LOGGING__DIR']

if 'PHENOMEDB__DATA__PROJECT_DATA_BASE_PATH' in os.environ:
     config['DATA']['project_data_base_path'] = os.environ['PHENOMEDB__DATA__PROJECT_DATA_BASE_PATH']

if 'PHENOMEDB__DATA__APP_DATA' in os.environ:
     config['DATA']['app_data'] = os.environ['PHENOMEDB__DATA__APP_DATA']

if 'PHENOMEDB__DATA__COMPOUNDS' in os.environ:
    config['DATA']['compounds'] = os.environ['PHENOMEDB__DATA__COMPOUNDS']

if 'PHENOMEDB__DATA__SQL' in os.environ:
    config['DATA']['sql'] = os.environ['PHENOMEDB__DATA__SQL']

if 'PHENOMEDB__DATA__CONFIG' in os.environ:
     config['DATA']['config'] = os.environ['PHENOMEDB__DATA__CONFIG']

if 'PHENOMEDB__DATA__CACHE' in os.environ:
     config['DATA']['cache'] = os.environ['PHENOMEDB__DATA__CACHE']

if 'PHENOMEDB__DATA__NGINX_CACHE' in os.environ:
     config['DATA']['nginx_cache'] = os.environ['PHENOMEDB__DATA__NGINX_CACHE']

if 'PHENOMEDB__DATA__TASK_DIRECTORY' in os.environ:
     config['DATA']['task_directory'] = os.environ['PHENOMEDB__DATA__TASK_DIRECTORY']

if 'PHENOMEDB__R__SCRIPT_DIRECTORY' in os.environ:
     config['R']['script_directory'] = os.environ['PHENOMEDB__R__SCRIPT_DIRECTORY']

if 'PHENOMEDB__R__EXEC_PATH' in os.environ:
     config['R']['exec_path'] = os.environ['PHENOMEDB__R__EXEC_PATH']

if 'PHENOMEDB__DATA__TEST_DATA' in os.environ:
     config['DATA']['test_data'] = os.environ['PHENOMEDB__DATA__TEST_DATA']

if 'PHENOMEDB__PIPELINES__PIPELINE_MANAGER' in os.environ:
     config['PIPELINES']['pipeline_manager'] = os.environ['PHENOMEDB__PIPELINES__PIPELINE_MANAGER']

if 'PHENOMEDB__PIPELINES__PIPELINE_MANAGER' in os.environ:
     config['PIPELINES']['task_spec_file'] = os.environ['PHENOMEDB__PIPELINES__TASK_SPEC_FILE']

if 'PHENOMEDB__PIPELINES__PIPELINE_FOLDER' in os.environ:
     config['PIPELINES']['pipeline_folder'] = os.environ['PHENOMEDB__PIPELINES__PIPELINE_FOLDER']

if 'PHENOMEDB__PIPELINES__PIPELINE_MANAGER_API_HOST' in os.environ:
     config['PIPELINES']['pipeline_manager_api_host'] = os.environ['PHENOMEDB__PIPELINES__PIPELINE_MANAGER_API_HOST']

if 'PHENOMEDB__PIPELINES__PIPELINE_MANAGER_USER' in os.environ:
     config['PIPELINES']['pipeline_manager_user'] = os.environ['PHENOMEDB__PIPELINES__PIPELINE_MANAGER_USER']

if 'PHENOMEDB__PIPELINES__PIPELINE_MANAGER_PASSWORD' in os.environ:
     config['PIPELINES']['pipeline_manager_password'] = os.environ['PHENOMEDB__PIPELINES__PIPELINE_MANAGER_PASSWORD']

if 'PHENOMEDB__PIPELINES__DOCKER' in os.environ:
     config['PIPELINES']['docker'] = os.environ['PHENOMEDB__PIPELINES__DOCKER']

if 'PHENOMEDB__API_KEYS__METABOLIGHTS' in os.environ:
     config['API_KEYS']['metabolights'] = os.environ['PHENOMEDB__API_KEYS__METABOLIGHTS']

if 'PHENOMEDB__API_KEYS__CHEMSPIDER' in os.environ:
     config['API_KEYS']['chemspider'] = os.environ['PHENOMEDB__API_KEYS__CHEMSPIDER']

