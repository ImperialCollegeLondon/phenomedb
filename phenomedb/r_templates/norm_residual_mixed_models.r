{% extends base_template %}
### Algorithm
## 1. open data csV
## 2. run IARC normalization_residualMixedModels
## 4. export results to csv

# This function is reproduced with permission from https://code.iarc.fr/viallonv/pipeline_biocrates
# Paper: "A New Pipeline for the Normalization and Pooling of Metabolomics Data"
# Metabolites
# 2021-09-17 | Journal article
# DOI: 10.3390/metabo11090631
# https://doi.org/10.3390/metabo11090631


{% block methodspecific %}
##############################################################################################
#
#                   "normalization" of metabolite levels, to remove unwanted sources of variation
#                   such as batch/study effect, etc.
#
#

### DATA: a list of objects including
#   * data.metabo : data.frame (or tibble) of dim. n x (K+p) with
#     - n : number of observations
#     - p : number of metabolites
#     - K : number of variables used for the unique identification of the individuals (see input forIdentifier below)
#   * others :  data.frame (or tibble) of n x (K+d): unique identifiers + "all other" variables (country, Cncr_Caco, age, bmi, etc.): any variable that can be useful in the final analysis (after the normalization)
#   * aux :  p x 3 matrix indicating for each metabolite, its Name, Class, and Type (semi-quantified vs quantified) (colnames= "Name", "Class", and "Type"))
# forIdentifier: vector of strings, indicating the names of the variables used for the unique identification of individuals
# A unique identifier IdentifierPipeline will be created, and the output data are ordered by IdentifierPipeline
### listRandom: vector of strings, containing the names of the variables for modelled as random effects, whose effects on the measurements will be removed
#       if HeteroSked is not NULL, then this vector has to be either of length 1 (one variable only), or made of variables whose random effects are nested: e.g., Laboratory, Study, Batch
#       (and Heterosked has to be one of these variables)
#       if Heterosked is NULL, and some random variables have to be nested, the corresponding variables have to be nested "by construction", as is the case for the Study and
#       Batch variables in the Metabolomics data: more precisely, Batch levels are like BREA_01_01, for the 1st batch of study BREA_01.
###  listFixedToKeep: vectors of strings, containing the names of the variables modelled as fixed effects, and whose effects on the measurements will be kept (e.g. Gender, or Bmi)
###  listFixedToRemove: vectors of strings, containing the names of the variables modelled as fixed effects, and whose effects on the measurements will be removed (e.g., Center or Country)
# Remark: if some missing values are present in variables in listFixedToKeep and/or listFixedToRemove, normalized measurements will be missing for the corresponding samples
#         * if this is not desirable, you have to impute missing values in variables in listFixedToKeep and/or listFixedToRemove first
### HeteroSked : NULL by default (no correction for heteroskedasticity) otherwise the name of one variable, for which heteroscedasticity will be accounted for
# ### in this case, listRandom has to contain this variable, and has to be either a vector of 1 variable only, or a vector of nested variables
# for example,  listRandom =  c("Study", "Batch"), with Batch nested within studies, and HeteroSked= "Batch" (usually very long to compute) or HeteroSked="Study",
# if variances of the residuals vary with Batch or Study, respectively.
#
# Output :
# o a new DATA (with entries data, others, aux, just as the input DATA list) where unwanted variation has been removed
#
#
# library(tidyverse)
# library(reshape2)
# library(hglm)
# library(nlme)
# library(lme4)
#
##############################################################################################

# listRandom = c("Batch", "Study")
# listFixed= c("Bmi_C")

normalization_residualMixedModels <- function(DATA, forIdentifier = c("Study", "Batch", "CaseSet", "Idepic"),
                                              listRandom=NULL, listFixedToKeep=NULL,
                                              listFixedToRemove=NULL, HeteroSked=NULL) {


  data.metabo  <- as_tibble(DATA$data.metabo)  %>%
    unite(IdentifierPipeline, all_of(forIdentifier), sep="", remove=F) %>%
    arrange(IdentifierPipeline)
  others       <- as_tibble(DATA$others)  %>%
    unite(IdentifierPipeline, all_of(forIdentifier), sep="", remove=F) %>%
    arrange(IdentifierPipeline)
  aux          <- as_tibble(DATA$aux)

  index.metabo <- which(colnames(DATA$data.metabo) %in% aux$Name)
  namesMet     <- colnames(DATA$data.metabo)[index.metabo]

  var.context = unique(c("IdentifierPipeline", forIdentifier, listRandom, listFixedToKeep, listFixedToRemove)) #c("Idepic", "Batch", "Study")

  # Detach DATA

  if (sum(data.metabo$IdentifierPipeline == others$IdentifierPipeline) < nrow(data.metabo)) {stop("Idepic should be the same in data.metabo and others")}

  data    <- left_join( data.metabo,
                        others %>% dplyr::select(all_of(var.context)) %>% dplyr::select(-any_of(forIdentifier)),
                        by= "IdentifierPipeline") %>%
    dplyr::select(all_of(var.context), all_of(namesMet))




  # data preparation
  data <- reshape2::melt(data, id.vars = which(colnames(data)%in% var.context), value.name = "Y", variable.name = "Metabo")
  data <- data %>% arrange(across(c("Metabo", all_of(var.context))))
  data.context        <- data[1:table(data$Metabo)[[1]], 1:length(var.context)]
  data.context.hetero <- data[1:table(data$Metabo)[[1]], 1:length(var.context)]

  # --------------------------------------------------------------------------------------------
  # Remove unwanted effects ...
  # --------------------------------------------------------------------------------------------

  Metabolites <- unique(data$Metabo)


  for (i in Metabolites)
  {
    cat(i, "\n")
    data.met <- data %>% filter(Metabo == i)
    Res <- FUNnormalization_residualMixedModels(data=data.met, listRandom=listRandom,
                                            listFixedToKeep=listFixedToKeep, listFixedToRemove=listFixedToRemove, HeteroSked=HeteroSked, i=i)
    data.context <- cbind(data.context, Res)

  }

  #Coef <- list(Rho.Batch = Rho.Batch, Est.Batch = Est.Batch, Est.Indiv = Est.Indiv, Est.Study = Est.Study)
  colnames(data.context) <- c(var.context, as.character(Metabolites))
  data.context <- as_tibble(data.context)
  data.context <- data.context %>% arrange(IdentifierPipeline) %>% dplyr::select(-IdentifierPipeline)
  others       <- others  %>% arrange(IdentifierPipeline) %>% dplyr::select(-IdentifierPipeline)
  #others <- others %>% arrange(across(all_of(var.context)))

  return(list(data = data.context, others= others, aux = aux))
  }


FUNnormalization_residualMixedModels <- function(data, listRandom, listFixedToKeep, listFixedToRemove, HeteroSked, i) {

  listFixedInit <- c(listFixedToKeep, listFixedToRemove)
  if (is.null(c(listFixedToKeep, listFixedToRemove))) {listFixed <- "1"} else {listFixed <- listFixedInit}
  #X <- model.matrix(~1, data = data)
  y <- data$Y


  ####### Now, we compute residuals to correct for Batch, etc... effects

  datalmer0               <- cbind.data.frame(y=y, data[, c(listRandom, listFixedInit)])
  colnames(datalmer0)[-1] <- c(listRandom, listFixedInit)
  indNoNAs                <- which(rowSums(is.na(datalmer0))==0)
  datalmer                <- datalmer0[indNoNAs,]
  Y1                      <- rep(NA, length(y))
  if (!is.null(listFixedToKeep))
  {
    datatemp <- data.frame(datalmer[, listFixedToKeep])
    colnames(datatemp) <- listFixedToKeep
    XFixedToKeep <- model.matrix(~ ., data= datatemp)
  }

  if (is.null(HeteroSked))
  {
    textformulaMixed   <- paste("y~", paste0(listFixed, collapse="+"), paste0("+(1|", paste0(listRandom, collapse=")+(1|"), ")"))
    tochecklmer <- tryCatch(lmer(as.formula(textformulaMixed), data= datalmer,
                                 control=lmerControl(optimizer="bobyqa", optCtrl=list(maxfun=2e5))),
                            error=function(e) NULL)
    if (!is.null(tochecklmer))
    {
      if (!is.null(listFixedToKeep))
      {
        Y1[indNoNAs] <- XFixedToKeep %*% matrix(fixef(tochecklmer)[names(fixef(tochecklmer))%in%colnames(XFixedToKeep)], ncol=1) + resid(tochecklmer) # predict(tochecklmer, re.form=NA) + resid(tochecklmer)
      }else{ Y1[indNoNAs] <- mean(y) + resid(tochecklmer)}

    }
  }else
  {
    listrandomeffect <- vector(mode = "list", length = length(listRandom))
    for (kli in 1:length(listRandom))
    {
      listrandomeffect[[kli]] <- as.formula(paste0("~1|", listRandom[kli]))
    }
    forweights <- as.formula(paste0("~1|", HeteroSked))

    textformulaFixedHeteroSked<- paste("y~", paste0(listFixed, collapse="+"))

    tochecklme <- tryCatch(lme(as.formula(textformulaFixedHeteroSked), random =  listrandomeffect, weights = varIdent(form=forweights),
                               data = datalmer,
                               control = list(maxIter = 900, msMaxIter = 900, niterEM = 900, msMaxEval = 900, opt = "optim")),
                           error=function(e) NULL)

    if (!is.null(tochecklme))
    {
      forrescale <- sd(residuals(tochecklme, type="pearson"))/sd(residuals(tochecklme))
      if (!is.null(listFixedToKeep))
      {
        Y1[indNoNAs] <- XFixedToKeep%*%matrix(fixed.effects(tochecklme)[names(fixef(tochecklme))%in%colnames(XFixedToKeep)], ncol=1) +
                        residuals(tochecklme, type = "pearson")/forrescale
      }else
      {
        Y1[indNoNAs] <- mean(y) + residuals(tochecklme, type = "pearson")/forrescale
      }
    }
  }

  return(Y1)
}

library(tidyverse)
library(reshape2)
library(hglm)
library(nlme)
library(lme4)

#intensity_data <- data.matrix(read.csv('{{ intensity_data_file_path }}'))
#sample_metadata <- read.csv('{{ sample_metadata_file_path }}',stringsAsFactors=T)

data.metabo <- read.csv('{{ metabo_file_path }}')
others <- read.csv('{{ others_file_path }}',stringsAsFactors=T)
#aux <- read.csv('{{ aux_file_path }}',stringsAsFactors=T)
aux <- read.csv('{{ aux_file_path }}')
#sample_ids <- data.frame('Sample.File.Name'=sample_metadata$Sample.File.Name)
#data.metabo <- cbind(sample_ids,intensity_data)
#DATA.Imp <- cbind(sample_ids,intensity_data)
#others <- sample_metadata
DATA = list(data.metabo=data.metabo,others=others,aux=aux)
forIdentifier <- c('{{ identifier_column | replace(' ','.') }}',"{{ '","'.join(columns_random_to_correct) | replace(' ','.')}}")
listRandom <- c("{{ '","'.join(columns_random_to_correct) | replace(' ','.')}}")
{% if columns_fixed_to_keep | length > 0 %}
listFixedToKeep <- c("{{ '","'.join(columns_fixed_to_keep) | replace('::','..')}}")
{% else %}
listFixedToKeep <- NULL
{% endif %}
{% if columns_fixed_to_correct | length > 0 %}
listFixedToRemove <- c("{{ '","'.join(columns_fixed_to_correct) | replace(' ','.')}}")
{% else %}
listFixedToRemove <- NULL
{% endif %}
{% if heteroscedastic_columns | length > 0 %}
HeteroSked <- c("{{ '","'.join(heteroscedastic_columns) | replace(' ','.')}}")
{% else %}
HeteroSked <- NULL
{% endif %}
DATA.Normalized <- normalization_residualMixedModels(DATA,
                                                 forIdentifier = forIdentifier,
                                                 listRandom = listRandom, listFixedToKeep= listFixedToKeep,
                                                 listFixedToRemove=listFixedToRemove, HeteroSked=HeteroSked)
output <- DATA.Normalized

{% endblock %}

