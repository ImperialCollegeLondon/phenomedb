
var plotly_settings = {
    responsive:true,
    modeBarButtonsToRemove: ['toImage', 'sendDataToCloud'],
    modeBarButtonsToAdd: [{
        name: 'toImageSVG',
        icon: Plotly.Icons.camera,
        click: function (gd) {
            let title = $(gd).find('.gtitle').data('unformatted');
            title = title.replaceAll(":","_").replaceAll('<br />','_').replaceAll('/',"_").replaceAll(" ","_");
            title = title + "_" + (new Date().toJSON().slice(0,22)).replaceAll("-","").replaceAll(":","").replaceAll(".","");
            Plotly.downloadImage(gd, {format: 'svg',filename: title});
        }
    }],
}

function get_layout(title,barmode=null){
    var layout = {
            height: 600,
            width: 600,
            title: {
                text:title,
                font: {
                    family: 'Droid Sans',
                    size: 16
                },
                xref: 'paper',
                x: 0.05,
            },
        };
    if (barmode !== undefined){
        layout['barmode'] = barmode;
    }
    return layout;
}
var data1 = [{
    values: [],
    labels: [],
    type: 'pie',
    marker: {colors: []},
}];
{% for project,count in data.saved_query_summary_stats.project_counts.items() %}
    data1[0]['values'].push({{ count }});
    data1[0]['labels'].push('{{ project }}');
    data1[0]['marker']['colors'].push('{{ data.project_colours[project]}}');
{% endfor %}
console.log(data1);
Plotly.newPlot('pie_chart_one', data1, get_layout('SampleAssay counts by project'),plotly_settings);

var data2 = [{
    values: [],
    labels: [],
    type: 'pie'
}];
{% for assay,count in data.saved_query_summary_stats.assay_counts.items() %}
    data2[0]['values'].push({{ count }});
    data2[0]['labels'].push('{{ assay }}');
{% endfor %}
Plotly.newPlot('pie_chart_two', data2, get_layout('SampleAssay counts by assay'),plotly_settings);

var data3 = [{
    values: [],
    labels: [],
    type: 'pie'
}];
{% for sample_matrix,count in data.saved_query_summary_stats.sample_matrix_counts.items() %}
    data3[0]['values'].push({{ count }});
    data3[0]['labels'].push('{{ sample_matrix }}');
{% endfor %}
Plotly.newPlot('pie_chart_three', data3, get_layout('SampleAssay counts by sample matrix'),plotly_settings);

var data4 = [{
    values: [],
    labels: [],
    type: 'pie'
}];
{% for sample_type,count in data.saved_query_summary_stats.sample_type_counts.items() %}
    data4[0]['values'].push({{ count }});
    data4[0]['labels'].push('{{ sample_type }}');
{% endfor %}
Plotly.newPlot('pie_chart_four', data4, get_layout('SampleAssay counts by sample type'));

var harmonised_numeric_metadata_counts_by_project = {};
{% for metadata_field_name,project_counts in data.saved_query_summary_stats.metadata_counts_harmonised_numeric_by_project.items() %}
    //if ($('#metadata_harmonised_text_by_project_{{ metadata_field_name }}').length == 0){
        if (harmonised_numeric_metadata_counts_by_project['{{ metadata_field_name }}'] === undefined) {
            harmonised_numeric_metadata_counts_by_project['{{ metadata_field_name }}'] = {}
        }
        var plot_data = [];
        {% for project_name, metadata_values in project_counts.items() %}

            if (harmonised_numeric_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'] === undefined) {
                harmonised_numeric_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'] = {}
            }
            harmonised_numeric_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'] = {
                x: [],
                y: [],
                type: 'bar',
                name: '{{ project_name }}',
                marker: {color: '{{ data.project_colours[project_name]}}'}
            };
            {% for metadata_value, value_count in metadata_values.items() %}
                harmonised_numeric_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}']['x'].push('{{ metadata_value }}');
                harmonised_numeric_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}']['y'].push({{ value_count }});
            {% endfor %}
            plot_data.push(harmonised_numeric_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'])
        {% endfor %}
        Plotly.newPlot('metadata_harmonised_numeric_by_project_{{ metadata_field_name }}_stack',plot_data,get_layout('Harmonised Numeric Metadata {{ metadata_field_name }} counts by project (stacked)','stack'),plotly_settings);
        Plotly.newPlot('metadata_harmonised_numeric_by_project_{{ metadata_field_name }}_group',plot_data,get_layout('Harmonised Numeric Metadata {{ metadata_field_name }} counts by project (grouped)','group'),plotly_settings);
    //}
{% endfor %}

var harmonised_text_metadata_counts_by_project = {};
{% for metadata_field_name,project_counts in data.saved_query_summary_stats.metadata_counts_harmonised_text_by_project.items() %}
    //if ($('#metadata_harmonised_text_by_project_{{ metadata_field_name }}').length == 0){
        if (harmonised_text_metadata_counts_by_project['{{ metadata_field_name }}'] === undefined) {
            harmonised_text_metadata_counts_by_project['{{ metadata_field_name }}'] = {}
        }
        var plot_data = [];
        {% for project_name, metadata_values in project_counts.items() %}

            if (harmonised_text_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'] === undefined) {
                harmonised_text_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'] = {}
            }
            harmonised_text_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'] = {
                x: [],
                y: [],
                type: 'bar',
                name: '{{ project_name }}',
                marker: {color: '{{ data.project_colours[project_name]}}'}
            };

            {% for metadata_value, value_count in metadata_values.items() %}
                harmonised_text_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}']['x'].push('{{ metadata_value }}');
                harmonised_text_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}']['y'].push({{ value_count }});
            {% endfor %}

            plot_data.push(harmonised_text_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'])
        {% endfor %}
        Plotly.newPlot('metadata_harmonised_text_by_project_{{ metadata_field_name }}_stack',plot_data,get_layout('Harmonised Text Metadata {{ metadata_field_name }} counts by project (stacked)','stack'),plotly_settings);
        Plotly.newPlot('metadata_harmonised_text_by_project_{{ metadata_field_name }}_group',plot_data,get_layout('Harmonised Text Metadata {{ metadata_field_name }} counts by project (grouped)','group'),plotly_settings);
    //}
{% endfor %}

var harmonised_datetime_metadata_counts_by_project = {};
{% for metadata_field_name,project_counts in data.saved_query_summary_stats.metadata_counts_harmonised_datetime_by_project.items() %}
    //if ($('#metadata_harmonised_text_by_project_{{ metadata_field_name }}').length == 0){
        if (harmonised_datetime_metadata_counts_by_project['{{ metadata_field_name }}'] === undefined) {
            harmonised_datetime_metadata_counts_by_project['{{ metadata_field_name }}'] = {}
        }
        var plot_data = [];
        {% for project_name, metadata_values in project_counts.items() %}

            if (harmonised_datetime_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'] === undefined) {
                harmonised_datetime_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'] = {}
            }
            harmonised_datetime_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'] = {
                x: [],
                y: [],
                type: 'bar',
                name: '{{ project_name }}',
                marker: {color: '{{ data.project_colours[project_name]}}'}
            };

            {% for metadata_value, value_count in metadata_values.items() %}
                harmonised_datetime_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}']['x'].push('{{ metadata_value }}');
                harmonised_datetime_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}']['y'].push({{ value_count }});
            {% endfor %}
            plot_data.push(harmonised_datetime_metadata_counts_by_project['{{ metadata_field_name }}']['{{ project_name }}'])
        {% endfor %}
        Plotly.newPlot('metadata_harmonised_datetime_by_project_{{ metadata_field_name }}_stack',plot_data,get_layout('Harmonised Datetime Metadata {{ metadata_field_name }} counts by project (stacked)','stack'),plotly_settings);
        Plotly.newPlot('metadata_harmonised_datetime_by_project_{{ metadata_field_name }}_group',plot_data,get_layout('Harmonised Datetime Metadata {{ metadata_field_name }} counts by project (grouped)','group'),plotly_settings);
    //}
{% endfor %}
{# for metadata_field_name,metadata_values in data.saved_query_summary_stats.metadata_counts_raw.items() #}

    //var raw_metadata_counts_{{ metadata_field_name | replace(" ","_") | replace("?","") }} = [{
    //    x: [],
    //    y: [],
    //    type: 'bar'
    //}];
    {# for metadata_value, value_count in metadata_values.items() #}
    //    raw_metadata_counts_{{ metadata_field_name | replace(" ","_") | replace("?","") }}[0]['x'].push('{{ metadata_value }}');
    //    raw_metadata_counts_{{ metadata_field_name | replace(" ","_") | replace("?","") }}[0]['y'].push({{ value_count }});
    {# endfor #}

    //console.log('{{ metadata_field_name }}');
    //    console.log(raw_metadata_counts_{{ metadata_field_name | replace(" ","_") | replace("?","")}});
    //    Plotly.newPlot('metadata_raw_{{ metadata_field_name | replace(" ","_") | replace("?","") }}',raw_metadata_counts_{{metadata_field_name | replace(" ","_") | replace("?","")}},get_layout('Raw Metadata {{ metadata_field_name }} counts'));

{# endfor #}

