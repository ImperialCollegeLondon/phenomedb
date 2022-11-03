#update.packages()
#install.packages("remotes")
#remotes::install_github("skgrange/threadr")
library(threadr)
library(jsonlite)
output_folder = '{{ output_folder }}'
setwd('{{ job_folder }}')
{% block methodspecific %}{% endblock %}
results <- toJSON(output,force=T,digits=NA)
output_file_path <- paste(output_folder,'results.json',sep='/')
write_json(results,output_file_path,pretty=F)
summary(output)
