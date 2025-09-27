FROM temporalio/server:1.28.1

# Docker context is set to the root of this repo
COPY server/config/dynamicconfig.yaml /etc/temporal/dynamicconfig.yaml
COPY server/config/dynamicconfig_es.yaml /etc/temporal/dynamicconfig_es.yaml
COPY server/config/config_template.yaml /etc/temporal/config/config_template.yaml
