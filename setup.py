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
    setup_requires=['numpy'],
    install_requires=[
        #'async_timeout<4.0,>=3.0',
        'pendulum==2.0.5',
        #'cachelib<0.10.0,>=0.9.0',
        #'httpx~=0.23.0',
        'sqlalchemy~=1.4.0',
        'pandas~=1.5.0',
        'numpy~=1.23.3',
        'nPYc',
        'redis',
        #'apache-airflow[password]~=2.5.1',
        'chemspipy',
        'xlrd',
        'pyarrow',
        'rdkit',
        'pytest',
        "pymzml[full]",
        'libchebipy'
    ]
)