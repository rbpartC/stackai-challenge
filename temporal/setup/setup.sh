#!/bin/bash

set -eu -o pipefail

# === Auto setup defaults ===

: "${DB:=cassandra}"
: "${SKIP_SCHEMA_SETUP:=false}"
: "${SKIP_DB_CREATE:=false}"
: "${DBNAME:=temporal}"


: "${VISIBILITY_DBNAME:=temporal_visibility}"
: "${POSTGRES_PORT:=5432}"

: "${MYSQL_SEEDS:=}"
: "${MYSQL_USER:=}"
: "${MYSQL_PWD:=}"
: "${MYSQL_TX_ISOLATION_COMPAT:=false}"

: "${POSTGRES_SEEDS:=}"
: "${POSTGRES_USER:=}"
: "${POSTGRES_PWD:=}"
: "${POSTGRES_DBNAME:=}"


: "${POSTGRES_TLS_ENABLED:=false}"
: "${POSTGRES_TLS_DISABLE_HOST_VERIFICATION:=true}"
: "${POSTGRES_TLS_CERT_FILE:=}"
: "${POSTGRES_TLS_KEY_FILE:=}"
: "${POSTGRES_TLS_CA_FILE:=}"
: "${POSTGRES_TLS_SERVER_NAME:=}"

# Elasticsearch
: "${ENABLE_ES:=false}"
: "${ES_SCHEME:=http}"
: "${ES_SEEDS:=}"
: "${ES_PORT:=9200}"
: "${ES_USER:=}"
: "${ES_PWD:=}"
: "${ES_VERSION:=v7}"
: "${ES_VIS_INDEX:=temporal_visibility_v1_dev}"
: "${ES_SEC_VIS_INDEX:=}"
: "${ES_SCHEMA_SETUP_TIMEOUT_IN_SECONDS:=0}"

# Server setup
: "${TEMPORAL_ADDRESS:=}"
: "${TEMPORAL_HOME:=/etc/temporal}"

: "${SKIP_DEFAULT_NAMESPACE_CREATION:=false}"
: "${DEFAULT_NAMESPACE:=default}"
: "${DEFAULT_NAMESPACE_RETENTION:=24h}"

: "${SKIP_ADD_CUSTOM_SEARCH_ATTRIBUTES:=false}"

# === Helper functions ===

die() {
    echo "$*" 1>&2
    exit 1
}

# === Main database functions ===

validate_db_env() {
    case ${DB} in
      postgres12 | postgres12_pgx)
          if [[ -z ${POSTGRES_SEEDS} ]]; then
              die "POSTGRES_SEEDS env must be set if DB is ${DB}."
          fi
          ;;
      *)
          die "Unsupported driver specified: 'DB=${DB}'. Valid drivers are: mysql8, postgres12, postgres12_pgx, cassandra."
          ;;
    esac
}


wait_for_postgres() {
    until nc -z "${POSTGRES_SEEDS}" "${POSTGRES_PORT}"; do
        echo "Waiting for PostgreSQL ${POSTGRES_SEEDS} ${POSTGRES_PORT} to startup."
        sleep 1
    done

    echo 'PostgreSQL started.'
}

wait_for_db() {
    case ${DB} in
      postgres12 | postgres12_pgx)
          wait_for_postgres
          ;;
      *)
          die "Unsupported DB type: ${DB}."
          ;;
    esac
}

setup_postgres_schema() {
    # TODO (alex): Remove exports
    export SQL_PASSWORD=${POSTGRES_PWD}

    POSTGRES_VERSION_DIR=v12
    SCHEMA_DIR=${TEMPORAL_HOME}/schema/postgresql/${POSTGRES_VERSION_DIR}/temporal/versioned
    # Create database only if its name is different from the user name. Otherwise PostgreSQL container itself will create database.
    if [[ ${POSTGRES_DBNAME} != "${POSTGRES_USER}" && ${SKIP_DB_CREATE} != true ]]; then
        echo "Creating database ${POSTGRES_DBNAME}."
        /usr/local/bin/temporal-sql-tool \
            --plugin ${DB} \
            --ep "${POSTGRES_SEEDS}" \
            -u "${POSTGRES_USER}" \
            -p "${POSTGRES_PORT}" \
            --db "${POSTGRES_DBNAME}" \
            --tls="true" \
            --tls-disable-host-verification="true" \
            create
    fi
    echo "Settiong schema"
    /usr/local/bin/temporal-sql-tool \
        --plugin ${DB} \
        --ep "${POSTGRES_SEEDS}" \
        -u "${POSTGRES_USER}" \
        -p "${POSTGRES_PORT}" \
        --db "${POSTGRES_DBNAME}" \
        --tls="${POSTGRES_TLS_ENABLED}" \
        --tls-disable-host-verification="${POSTGRES_TLS_DISABLE_HOST_VERIFICATION}" \
        setup-schema -v 0.0
    echo "Updating schema"
    /usr/local/bin/temporal-sql-tool \
        --plugin ${DB} \
        --ep "${POSTGRES_SEEDS}" \
        -u "${POSTGRES_USER}" \
        -p "${POSTGRES_PORT}" \
        --db "${POSTGRES_DBNAME}" \
        --tls="${POSTGRES_TLS_ENABLED}" \
        --tls-disable-host-verification="${POSTGRES_TLS_DISABLE_HOST_VERIFICATION}" \
        update-schema -d "${SCHEMA_DIR}"

    # Only setup visibility schema if ES is not enabled
    if [[ ${ENABLE_ES} == false ]]; then
      VISIBILITY_SCHEMA_DIR=${TEMPORAL_HOME}/schema/postgresql/${POSTGRES_VERSION_DIR}/visibility/versioned
      if [[ ${VISIBILITY_DBNAME} != "${POSTGRES_USER}" && ${SKIP_DB_CREATE} != true ]]; then
          /usr/local/bin/temporal-sql-tool \
              --plugin ${DB} \
              --ep "${POSTGRES_SEEDS}" \
              -u "${POSTGRES_USER}" \
              -p "${POSTGRES_PORT}" \
              --db "${VISIBILITY_DBNAME}" \
              --tls="${POSTGRES_TLS_ENABLED}" \
              --tls-disable-host-verification="${POSTGRES_TLS_DISABLE_HOST_VERIFICATION}" \
              --tls-cert-file "${POSTGRES_TLS_CERT_FILE}" \
              --tls-key-file "${POSTGRES_TLS_KEY_FILE}" \
              --tls-ca-file "${POSTGRES_TLS_CA_FILE}" \
              --tls-server-name "${POSTGRES_TLS_SERVER_NAME}" \
              create
      fi
      /usr/local/bin/temporal-sql-tool \
          --plugin ${DB} \
          --ep "${POSTGRES_SEEDS}" \
          -u "${POSTGRES_USER}" \
          -p "${POSTGRES_PORT}" \
          --db "${VISIBILITY_DBNAME}" \
          --tls="${POSTGRES_TLS_ENABLED}" \
          --tls-disable-host-verification="${POSTGRES_TLS_DISABLE_HOST_VERIFICATION}" \
          --tls-cert-file "${POSTGRES_TLS_CERT_FILE}" \
          --tls-key-file "${POSTGRES_TLS_KEY_FILE}" \
          --tls-ca-file "${POSTGRES_TLS_CA_FILE}" \
          --tls-server-name "${POSTGRES_TLS_SERVER_NAME}" \
          setup-schema -v 0.0
      /usr/local/bin/temporal-sql-tool \
          --plugin ${DB} \
          --ep "${POSTGRES_SEEDS}" \
          -u "${POSTGRES_USER}" \
          -p "${POSTGRES_PORT}" \
          --db "${VISIBILITY_DBNAME}" \
          --tls="${POSTGRES_TLS_ENABLED}" \
          --tls-disable-host-verification="${POSTGRES_TLS_DISABLE_HOST_VERIFICATION}" \
          --tls-cert-file "${POSTGRES_TLS_CERT_FILE}" \
          --tls-key-file "${POSTGRES_TLS_KEY_FILE}" \
          --tls-ca-file "${POSTGRES_TLS_CA_FILE}" \
          --tls-server-name "${POSTGRES_TLS_SERVER_NAME}" \
          update-schema -d "${VISIBILITY_SCHEMA_DIR}"
    fi
}

setup_schema() {
    case ${DB} in
      mysql8)
          echo 'Setup MySQL schema.'
          setup_mysql_schema
          ;;
      postgres12 | postgres12_pgx)
          echo 'Setup PostgreSQL schema.'
          setup_postgres_schema
          ;;
      cassandra)
          echo 'Setup Cassandra schema.'
          setup_cassandra_schema
          ;;
      *)
          die "Unsupported DB type: ${DB}."
          ;;
    esac
}

# === Elasticsearch functions ===

validate_es_env() {
    if [[ ${ENABLE_ES} == true ]]; then
        if [[ -z ${ES_SEEDS} ]]; then
            die "ES_SEEDS env must be set if ENABLE_ES is ${ENABLE_ES}"
        fi
    fi
}

wait_for_es() {
    SECONDS=0

    ES_SERVER="${ES_SCHEME}://${ES_SEEDS%%,*}:${ES_PORT}"

    until curl --silent --fail --user "${ES_USER}":"${ES_PWD}" "${ES_SERVER}" >& /dev/null; do
        DURATION=${SECONDS}

        if [[ ${ES_SCHEMA_SETUP_TIMEOUT_IN_SECONDS} -gt 0 && ${DURATION} -ge "${ES_SCHEMA_SETUP_TIMEOUT_IN_SECONDS}" ]]; then
            echo 'WARNING: timed out waiting for Elasticsearch to start up. Skipping index creation.'
            return;
        fi

        echo 'Waiting for Elasticsearch to start up.'
        sleep 1
    done

    echo 'Elasticsearch started.'
}

setup_es_index() {
    ES_SERVER="${ES_SCHEME}://${ES_SEEDS%%,*}:${ES_PORT}"
# @@@SNIPSTART setup-es-template-commands
    # ES_SERVER is the URL of Elasticsearch server i.e. "http://localhost:9200".
    SETTINGS_URL="${ES_SERVER}/_cluster/settings"
    SETTINGS_FILE=${TEMPORAL_HOME}/schema/elasticsearch/visibility/cluster_settings_${ES_VERSION}.json
    TEMPLATE_URL="${ES_SERVER}/_template/temporal_visibility_v1_template"
    SCHEMA_FILE=${TEMPORAL_HOME}/schema/elasticsearch/visibility/index_template_${ES_VERSION}.json
    INDEX_URL="${ES_SERVER}/${ES_VIS_INDEX}"
    curl --fail --user "${ES_USER}":"${ES_PWD}" -X PUT "${SETTINGS_URL}" -H "Content-Type: application/json" --data-binary "@${SETTINGS_FILE}" --write-out "\n"
    curl --fail --user "${ES_USER}":"${ES_PWD}" -X PUT "${TEMPLATE_URL}" -H 'Content-Type: application/json' --data-binary "@${SCHEMA_FILE}" --write-out "\n"
    curl --user "${ES_USER}":"${ES_PWD}" -X PUT "${INDEX_URL}" --write-out "\n"
    if [[ -n "${ES_SEC_VIS_INDEX}" ]]; then
      SEC_INDEX_URL="${ES_SERVER}/${ES_SEC_VIS_INDEX}"
      curl --user "${ES_USER}":"${ES_PWD}" -X PUT "${SEC_INDEX_URL}" --write-out "\n"
    fi
# @@@SNIPEND
}

# === Server setup ===

register_default_namespace() {
    echo "Registering default namespace: ${DEFAULT_NAMESPACE}."
    if ! temporal operator namespace describe "${DEFAULT_NAMESPACE}"; then
        echo "Default namespace ${DEFAULT_NAMESPACE} not found. Creating..."
        temporal operator namespace create --retention "${DEFAULT_NAMESPACE_RETENTION}" --description "Default namespace for Temporal Server." "${DEFAULT_NAMESPACE}"
        echo "Default namespace ${DEFAULT_NAMESPACE} registration complete."
    else
        echo "Default namespace ${DEFAULT_NAMESPACE} already registered."
    fi
}

add_custom_search_attributes() {
    until temporal operator search-attribute list --namespace "${DEFAULT_NAMESPACE}"; do
      echo "Waiting for namespace cache to refresh..."
      sleep 1
    done
    echo "Namespace cache refreshed."

    echo "Adding Custom*Field search attributes."
    # TODO: Remove CustomStringField
# @@@SNIPSTART add-custom-search-attributes-for-testing-command
    temporal operator search-attribute create --namespace "${DEFAULT_NAMESPACE}" \
        --name CustomKeywordField --type Keyword \
        --name CustomStringField --type Text \
        --name CustomTextField --type Text \
        --name CustomIntField --type Int \
        --name CustomDatetimeField --type Datetime \
        --name CustomDoubleField --type Double \
        --name CustomBoolField --type Bool
# @@@SNIPEND
}

# === Main ===

echo "Starting Temporal server setup."

if [[ ${SKIP_SCHEMA_SETUP} != true ]]; then
    validate_db_env
    wait_for_db
    setup_schema
fi

if [[ ${ENABLE_ES} == true ]]; then
    validate_es_env
    wait_for_es
    setup_es_index
fi

exit 0