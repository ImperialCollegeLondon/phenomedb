# cd docker/custom_images/phenomedb-airflow
# docker build -t ghaggart/phenomedb-airflow .
# docker push ghaggart/phenomedb-airflow

# ap && cd docker/custom_images/phenomedb-airflow && docker build -t ghaggart/phenomedb-airflow . && docker push ghaggart/phenomedb-airflow

FROM apache/airflow:latest-python3.9

ENV DEBIAN_FRONTEND=noninteractive

USER root
RUN apt-get update
RUN apt-get install -y gfortran libreadline6-dev libx11-dev libxt-dev libpng-dev libjpeg-dev libcairo2-dev xvfb libzstd-dev texinfo texlive texlive-fonts-extra screen wget zlib1g-dev libbz2-dev liblzma-dev libpcre2-dev libcurl4-openssl-dev openjdk-11-jdk build-essential wget
RUN wget https://cran.r-project.org/src/base/R-4/R-4.2.1.tar.gz
RUN tar zxvf R-4.2.1.tar.gz
RUN cd R-4.2.1 &&  ./configure --enable-R-shlib && make && make install && cd .. && rm -rf R-4.2.1
RUN apt install -y --no-install-recommends software-properties-common dirmngr
RUN apt-get install -y dirmngr apt-transport-https ca-certificates software-properties-common gnupg2
RUN apt-get install -y vim git xml2 libxml2-dev openssl libcurl4-openssl-dev curl libssl-dev libcurl4 libudunits2-dev libudunits2-dev libnetcdf-dev
RUN chown -R airflow /usr/local/lib/R/
RUN chmod -R 777 /usr/local/lib/R/
USER airflow
RUN pip install --upgrade nPYc
RUN pip install --upgrade pip
RUN pip install --upgrade pandas
RUN pip install --upgrade isatools
RUN pip install --upgrade markupsafe
RUN pip install --upgrade jinja2
RUN pip install --default-timeout=100 chemspipy xlrd redis pyarrow rdkit-pypi pytest azure-servicebus "pymzml[full]" libchebipy
RUN R -e "install.packages('jsonlite',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('remotes',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('BiocManager',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "remotes::install_github('skgrange/threadr',dependencies=TRUE)"
RUN R -e "BiocManager::install('sva')"
RUN R -e "remotes::install_github('s-u/unixtools',dependencies=TRUE)"
RUN R -e "remotes::install_github('JoeRothwell/pcpr2',dependencies=TRUE)"
RUN R -e "install.packages('tidyverse',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('foreach',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('reshape2',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('nlme',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('lme4',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('factoextra',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('ggrepel',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('ggpubr',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages('hglm',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "BiocManager::install('MWASTools')"
RUN R -e "BiocManager::install('xcms')"
RUN R -e "BiocManager::install('BiocParallel')"
