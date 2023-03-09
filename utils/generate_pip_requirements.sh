#!/bin/zsh
set -x
AIRFLOW_VERSION=2.5.1
PYTHON_VERSION=3.9
conda init zsh
conda deactivate
conda env remove -n phenomedb-build-requirements
conda create -n phenomedb-build-requirements python=$PYTHON_VERSION
conda activate phenomedb-build-requirements
pip install "apache-airflow[password]==${AIRFLOW_VERSION}" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
pip install chemspipy xlrd redis pyarrow rdkit-pypi pytest azure-servicebus "pymzml[full]" libchebip
pip install markupsafe==2.0.1
pip install isatools==0.12.2
#pip install --upgrade nPYc


#pip install -r requirements.txt.new
#pip install "apache-airflow[password]==${AIRFLOW_VERSION}" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
#set +x
#pip install apache-airflow==$AIRFLOW_VERSION --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
#pip freeze -r ./requirements.new
#pip install chemspipy xlrd redis pyarrow rdkit-pypi pytest azure-servicebus "pymzml[full]" libchebip
#pip install markupsafe==2.0.1
#pip install --upgrade nPYc
