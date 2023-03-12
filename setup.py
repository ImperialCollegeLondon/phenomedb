from distutils.core import setup
#requires = open('./requirements.txt').read().strip().split('\n')
setup(
    name='PhenomeDB',
    version='0.95',
    packages=['phenomedb'],
    license='',
    long_description='PhenomeDB is a platform for harmonisation and integration of multi-study metabolomics data.',
    author='Gordon A. Davies',
    author_email='phenomedb@proton.me',
    python_requires='==3.9',
   # setup_requires=["numpy"],
#dependency_links=['http://github.com/ghaggart/isa-api/tarball/master#egg=istaools-0.14.2'],
    install_requires=[
    #    'isatools @ git+https://github.com/ghaggart/isa-api/blob/master/dist/isatools-0.14.2-py3.9.egg=isatools',
        'nPYc',
    #    'redis'
    ]
     #                   'pendulum==2.0.5',
     #           'certifi==2021.5.30',
    #'jinja2~=3.0.1',
        #    'isatools @ git+https://github.com/ghaggart/isa-api/blob/master/dist/isatools-0.14.2-py3.9.egg=isatools',
                    #'isatools @ https://github.com/ghaggart/isa-api/blob/master/dist/isatools-0.14.2.tar.gz=isatools',
#'isatools==0.14.2',
                      #'apache-airflow[password]==2.4.3',
      #  'sqlalchemy',
      #               'nPYc',
      #               'pyChemometrics',
      #               'chemspipy',
      #               'xlrd',
      #               'redis',
      #                'pyarrow',
      #  'pandas',
      #  'numpy',
      #                'rdkit',
      #                  'pytest',
      #                "pymzml[full]",
      #                'libchebipy']
)