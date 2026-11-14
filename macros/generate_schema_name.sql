{# Dataset = <profile dataset>_<team folder>, e.g. teams/sales/ -> analytics_sales or ci_pr_42_sales.
   A model's +schema replaces the team folder, e.g. staging. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ target.schema }}_{{ custom_schema_name or node.original_file_path.split('/')[1] }}
{%- endmacro %}
