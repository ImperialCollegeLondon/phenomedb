from distutils.core import setup
#requires = open('./requirements.txt').read().strip().split('\n')
setup(
    name='phenomedb',
    version='0.9.8',
    packages=['phenomedb','phenomedb.views'],
    license='GPL-3.0-or-later',
    description='PhenomeDB is a platform for harmonisation and integration of multi-study metabolomics data, that uses Postgres, Apache-Airflow, and Redis.',
    long_description='PhenomeDB is a platform for harmonisation and integration of multi-study metabolomics data, that uses Postgres, Apache-Airflow, Redis, and the nPYc-Toolbox. Developed by the Phenome Centre at Imperial College London. Please see readthedocs for installation and usage. Copyright 2023 Imperial College London',
    author='Gordon A. Davies',
    author_email='phenomedb@proton.me',
    python_requires='>3.8, <3.10',
    setup_requires=['numpy'],
    install_requires=[
        'pendulum==2.0.5',
        'sqlalchemy~=1.4.0',
        'pandas~=1.5.0',
        'numpy~=1.23.3',
        'nPYc',
        'redis',
        'chemspipy',
        'psycopg2',
        'deepdiff',
        'xlrd',
        'pyarrow',
        'rdkit',
        'pytest',
        "pymzml[full]",
        'libchebipy'
    ],
    include_package_data=True,
    keywords=['phenomedb','metabolomics','LC-MS','NMR']
)