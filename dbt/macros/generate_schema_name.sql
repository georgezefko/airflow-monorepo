-- dev: everything in your personal dataset. prod: custom schema (staging, marts) as-is.
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ generate_schema_name_for_env(custom_schema_name, node) }}
{%- endmacro %}
