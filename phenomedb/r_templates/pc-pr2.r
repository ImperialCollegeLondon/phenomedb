{% extends base_template %}
### Algorithm
## 1. open data csv
## 2. import pcpr2
## 3. run pcpr2
## 4. export results to csv
### Dependencies:
## https://rdrr.io/github/skgrange/threadr/
## https://github.com/JoeRothwell/pcpr2
{% block methodspecific %}
#install.packages('devtools')
#library(devtools)
#install_github("JoeRothwell/pcpr2")
library(pcpr2)
intensity_chardata <- read.csv('{{ intensity_data_file_path }}')
intensity_data <- data.matrix(intensity_chardata)
sample_metadata <- read.csv('{{ sample_metadata_file_path }}',stringsAsFactors=T)
pct_threshold = {{ pct_threshold }}
pcpr2 <- try(runPCPR2(intensity_data, sample_metadata, pct.threshold = pct_threshold ))
if (inherits(pcpr2,"try-error")){
    pct_threshold <- pct_threshold - 0.1
    pcpr2 <- try(runPCPR2(intensity_data, sample_metadata, pct.threshold = pct_threshold))
}
if (inherits(pcpr2,"try-error")){
    pct_threshold <- pct_threshold - 0.1
    pcpr2 <- try(runPCPR2(intensity_data, sample_metadata, pct.threshold = pct_threshold))
}
if (inherits(pcpr2,"try-error")){
    pct_threshold <- pct_threshold - 0.1
    pcpr2 <- try(runPCPR2(intensity_data, sample_metadata, pct.threshold = pct_threshold))
}
if (inherits(pcpr2,"try-error")){
    pct_threshold <- pct_threshold - 0.1
    pcpr2 <- try(runPCPR2(intensity_data, sample_metadata, pct.threshold = pct_threshold))
}
if (inherits(pcpr2,"try-error")){
    pct_threshold <- pct_threshold - 0.1
    pcpr2 <- try(runPCPR2(intensity_data, sample_metadata, pct.threshold = pct_threshold))
}
if (inherits(pcpr2,"try-error")){
    pct_threshold <- pct_threshold - 0.1
    pcpr2 <- try(runPCPR2(intensity_data, sample_metadata, pct.threshold = pct_threshold))
}
if (inherits(pcpr2,"try-error")){
    pct_threshold <- pct_threshold - 0.1
    pcpr2 <- try(runPCPR2(intensity_data, sample_metadata, pct.threshold = pct_threshold))
}
if (inherits(pcpr2,"try-error")){
    pcpr2 <- try(runPCPR2(intensity_data, sample_metadata, pct.threshold = 0))
}
if(exists("pcpr2")){
    output <- pcpr2
    #output$pct_threshold = pct_threshold
}
{% endblock %}
