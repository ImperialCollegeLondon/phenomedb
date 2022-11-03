{% extends base_template %}
### Algorithm
## 1. open data csv
## 2. import SVA
## 3. run ComBat
## 4. export results to csv
### Dependencies:
## https://rdrr.io/github/skgrange/threadr/
## https://github.com/JoeRothwell/pcpr2
{% block methodspecific %}

#if (!require("BiocManager", quietly = TRUE))
#    install.packages("BiocManager")

#BiocManager::install("sva")
library('sva')
intensity_chardata <- read.csv('{{ intensity_data_file_path }}')
intensity_data <- data.matrix(intensity_chardata)
sample_metadata <- read.csv('{{ sample_metadata_file_path }}',stringsAsFactors=T)
#Y_variable =
#pheno = pData(dat)
#edata = exprs(dat)
#batch = pheno$batch
#mod = model.matrix(~as.factor(cancer), data=pheno)
{% if model_Y_variable and model_X_variables | length > 0 %}
X_matrix = sample_metadata[,c("{{ '","'.join(model_X_variables) | replace('::','..')}}")]
mod = model.matrix(~as.factor({{ model_Y_variable | replace('::','..') }}), data=X_matrix)
{% else %}
mod = NULL
{% endif %}
# parametric adjustment

#output = ComBat(dat=intensity_data, batch=sample_metadata$Unique.Batch, mod=NULL, par.prior=TRUE, prior.plots=FALSE)


# Log transforms and corrects with model
#output = t(ComBat(dat=t(log(intensity_data+1)), batch=sample_metadata${{ batch_variable }}, mod=mod, par.prior=TRUE, prior.plots=FALSE))

# Log transforms, corrects, then un-log transforms, with model
#output = t(ComBat(dat=t(intensity_data), batch=sample_metadata${{ batch_variable }}, mod=mod, par.prior=TRUE, prior.plots=FALSE))

output = t(ComBat(dat=t(intensity_data), batch=sample_metadata${{ batch_variable }}, mod=mod, par.prior=TRUE, prior.plots=FALSE))

{% endblock %}