{% extends base_template %}
### Algorithm
## 1. open data csv
## 2. import MWASTools
## 3. run MWASTools
## 4. export results to csv
### Dependencies:
## https://rdrr.io/github/skgrange/threadr/
## https://github.com/AndreaRMICL/MWASTools
{% block methodspecific %}

#if (!require("BiocManager", quietly = TRUE))
#    install.packages("BiocManager")

#BiocManager::install("MWASTools")
library('MWASTools')
intensity_data_frame <- read.csv('{{ data_file_path }}')
intensity_data <- data.matrix(intensity_data_frame,rownames.force=TRUE)
sample_metadata_dataframe <- read.csv('{{ sample_metadata_file_path }}',stringsAsFactors=T)
sample_metadata <- data.matrix(sample_metadata_dataframe,rownames.force=TRUE)
v <- integer(dim(intensity_data)[1])
se <- MWAS_SummarizedExperiment(intensity_data,sample_metadata,v)
mwastable <- MWAS_stats(se, disease_id = "{{ model_Y_variable | replace('::','..')}}",
{% if model_X_variables is iterable %}
                        confounder_ids = c("{{ '","'.join(model_X_variables) | replace('::','..') | replace(' ','.')}}"),
{% endif %}
                        assoc_method = '{{ method }}',mt_method = "{{ multiple_correction }}")

{% if method in ['linear','logistic'] %}
mwasmodels <- MWAS_stats(se, disease_id = "{{ model_Y_variable | replace('::','..')}}",output='models',
{% if model_X_variables is iterable %}
                       confounder_ids = c("{{ '","'.join(model_X_variables) | replace('::','..') | replace(' ','.')}}"),
{% endif %}
                       assoc_method = '{{ method }}',mt_method = "{{ multiple_correction }}")
metabolite_ids = rownames(mwastable)
mwasestimates = list()
mwassummaries = list()
for(i in 1:nrow(mwastable)){
    metabolite_id = metabolite_ids[i]
    summ <- summary(get(metabolite_id, mwasmodels))
    mwassummary = list(summ)
    mwassummaries <- append(mwassummaries,mwassummary)
    mwasestimate = list(summ$coefficients)
    mwasestimates <- append(mwasestimates,mwasestimate)
}
names(mwassummaries) <- metabolite_ids
names(mwasestimates) <- metabolite_ids

output <- list(as.data.frame(mwastable),mwasestimates,mwassummaries)
names(output) <- c('mwastable','mwasestimates','mwassummaries')
{% else %}
output <- list(as.data.frame(mwastable))
names(output) <- c('mwastable')
{% endif %}
#output <- c('mwas_table'=mwastable)
#{# if save_models #}
#mwasmodels <- MWAS_stats(se, disease_id = "{# model_Y_variable | replace('::','..')#}",
#                       confounder_ids = c("{# '","'.join(model_X_variables) | replace('::','..')#}"), assoc_method = '{# method #}',
#                       mt_method = "{# multiple_correction #}",output='models')
#output <- c(output,'mwas_models'=mwasmodels)
#{# endif #}
#{# if bootstrap #}
#mwasbootstraps <- c()
#metabolite_ids = rownames(mwastable)
#for(i in 1:nrow(mwastable)) {       # for-loop over rows
#  if(mwastable[i,'adjusted_pvalues']<=0.05){
#      metabolite_id <- metabolite_ids[i]
#      print(metabolite_id)
#       mwas_bootstrap <- MWAS_bootstrapping(se,disease_id = "{# model_Y_variable | replace('::','..')#}",metabolite_id=metabolite_id,confounder_ids = c("{# '","'.join(model_X_variables) | replace('::','..')#}"), assoc_method = '{# method #}')
#       mwasbootstraps <- c(mwasbootstraps,metabolite_id=mwas_bootstrap)
#  }
#}
#output <- c(output,'mwas_bootstraps'=mwasbootstraps)
#{# endif #}
{% endblock %}