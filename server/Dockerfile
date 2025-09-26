FROM temporalio/server:1.28.1

# Docker context is set to the root of this repo
COPY config/dynamicconfig.yaml /etc/temporal/dynamicconfig.yaml
COPY config/dynamicconfig_es.yaml /etc/temporal/dynamicconfig_es.yaml
COPY config/config_template.yaml /etc/temporal/config/config_template.yaml
COPY server/.bashrc /home/temporal/.bashrc
