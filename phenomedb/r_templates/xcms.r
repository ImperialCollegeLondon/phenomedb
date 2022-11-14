{% extends base_template %}

{% block methodspecific %}

#if (!require("BiocManager", quietly = TRUE))
#    install.packages("BiocManager")
if (!require("BiocManager", quietly = TRUE))
    install.packages("BiocManager")

#BiocManager::install("xcms")
#BiocManager::install("sva")
library('xcms')


#intensity_chardata <- read.csv('{{ mzml_path }}')
#intensity_data <- data.matrix(intensity_chardata)
#sample_metadata <- read.csv('{{ sample_metadata_file_path }}',stringsAsFactors=T)
#{% if model_Y_variable and model_X_variables | length > 0 %}
#X_matrix = sample_metadata[,c("{{ '","'.join(model_X_variables) | replace('::','..')}}")]
#mod = model.matrix(~as.factor({{ model_Y_variable | replace('::','..') }}), data=X_matrix)
#{% else %}
#mod = NULL
#{% endif %}

#output = t(ComBat(dat=t(intensity_data), batch=sample_metadata${{ batch_variable }}, mod=mod, par.prior=TRUE, prior.plots=FALSE))

{% endblock %}