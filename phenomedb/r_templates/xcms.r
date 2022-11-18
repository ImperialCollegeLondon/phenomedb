{% extends base_template %}

{% block methodspecific %}

#if (!require("BiocManager", quietly = TRUE))
#    install.packages("BiocManager")
if (!require("BiocManager", quietly = TRUE))
    install.packages("BiocManager")

#BiocManager::install("xcms")
#BiocManager::install("sva")
library('xcms')
source('{{ parse_IPC_project_folder_path }}')

# Paths to project
dataDirectory <- "{{ input_dir }}"

savePath <- "{{ output_path }}"

{% if lab == 'imperial' %}
study_files <- parse_IPC_MS_project_names("{{ input_dir }}", "{{ sample_matrix }}")
files = study_files$files
{% else %}
files = list.files("{{ input_dir }}", full.names=TRUE, pattern='.mzML')
{% endif %}
raw_data <- readMSData(files=files,mode="onDisk")

## Detect peaks
cwp <- CentWaveParam(prefilter=c({{ centwave_prefilter[0] }},{{ centwave_prefilter[1] }}),
                     peakwidth=c({{ centwave_peakwidth[0] }},{{ centwave_peakwidth[1] }}),
                     mzdiff={{ centwave_mzdiff }},
                     snthresh = {{ centwave_snthresh }},
                     ppm={{ centwave_ppm }},
                     noise={{ centwave_noise }},
                     mzCenterFun={{ centwave_wMean }},
                     integrate={{ centwave_integrate }})
xdata <- findChromPeaks(raw_data,
                        param=cwp)

# Sample groupings
# In this case the grouping is performed assuming 2 groups: one group with all study
# referencs and another with everything else
sample_group  <- study_files$metadata$sampleType
sample_group[sample_group != 'SR'] <- 'Samples'

## Perform peak grouping
pdp <- PeakDensityParam(sampleGroups=sample_group, #rep(1, length(fileNames(xdata))),
                        minFraction={{ peakdensity_minFraction }},#0,
                        minSamples={{ peakdensity_minSamples }},
                        bw={{ peakdensity_bw }},
                        binSize={{ peakdensity_binSize }})
xdata_gr <- groupChromPeaks(xdata,
                         param=pdp)

## Filling missing peaks
xdata <- fillChromPeaks(xdata_gr)
# Write final processed dataset
write.csv(peakTable(as(xdata_gr, 'xcmsSet')), file=savePath)
output = savePath

{% endblock %}