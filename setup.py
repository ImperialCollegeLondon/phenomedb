from distutils.core import setup
#requires = open('./requirements.txt').read().strip().split('\n')
setup(
    name='phenomedb',
    version='0.9.6',
    packages=['phenomedb','phenomedb.views'],
    license='',
    long_description='PhenomeDB is a platform for harmonisation and integration of multi-study metabolomics data.',
    author='Gordon A. Davies',
    author_email='phenomedb@proton.me',
    python_requires='<=3.9',
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
    include_package_data=True
)