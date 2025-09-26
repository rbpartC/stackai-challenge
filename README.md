## Part 1 - Deployment

### Deployment Sequence and Rationale

1. **Provision Databases**
   - The `temporal-core` PostgreSQL database is created first, as all Temporal services depend on it for state storage.
   - **Elasticsearch**: Deployed for visibility features (search, advanced queries). The password is auto-generated and passed to dependent services.

2. **Start Supporting Services**
   - **PG Bouncer**: Launched to provide connection pooling for PostgreSQL, improving performance and reliability.

3. **Initialize databases**
   - When using the temporal service container (and not the autosetup one), databases are not initialized with their appropriate schemas. You can deploy an admin-tools container as worker and enter it, then run the commands with the temporal-sql-tool to setup the psql schemas, and run the commands to configure the ES cluster and put the schema template, and create the visibility index. This container can be suspended after setting-up/upgrading schemas. The auto-setup script is actually a good way to understand the sequence and which commands to run.
   
      Command to run inside admin-tools create the PSQL schema (version of the schema depends on the version of temporal; I used latest versions of everything for simplicity)
   `
   ./temporal-sql-tool --ep $POSTGRES_SEEDS -p $POSTGRES_PORT -u $POSTGRES_USER --pw $POSTGRES_PASSWORD --db $DBNAME --pl postgres12 --tls create-schema -d schema/postgresql/v12/temporal/versioned
   `
      Commands to put ES settings and setup visibility index
   `
   ES_SERVER="${ES_SCHEME}://${ES_SEEDS%%,*}:${ES_PORT}"
   SETTINGS_URL="${ES_SERVER}/_cluster/settings"
   SETTINGS_FILE=${TEMPORAL_HOME}/schema/elasticsearch/visibility/cluster_settings_${ES_VERSION}.json
   TEMPLATE_URL="${ES_SERVER}/_template/temporal_visibility_v1_template"
   curl --fail --user "${ES_USER}":"${ES_PWD}" -X PUT "${SETTINGS_URL}" -H "Content-Type: application/json" --data-binary "@${SETTINGS_FILE}" --write-out "\n"
   curl --fail --user "${ES_USER}":"${ES_PWD}" -X PUT "${TEMPLATE_URL}" -H 'Content-Type: application/json' --data-binary "@${SCHEMA_FILE}" --write-out "\n"
   curl --user "${ES_USER}":"${ES_PWD}" -X PUT "${INDEX_URL}" --write-out "\n"
   `

4. **Deploy Temporal Services**
   - **Frontend, History, Matching, Worker**: Each Temporal service is deployed as a separate Docker service using the same Dockerfile but with different `SERVICES` environment variables. This separation allows for independent scaling and fault isolation.
   - **Worker**: Deployed after the history service to avoid startup errors.

5. **Deploy UI and Python Worker**
   - **Temporal UI**: Provides a web interface for monitoring and managing workflows.
   - **Python Worker**: For running custom workflow code.

**Rationale:**  
- Services are started in dependency order to avoid connection errors.  
- Environment variables are grouped and reused for consistency.  
- Docker runtime is used for portability and reproducibility.

Unfortunately, it seems that postgres database is not configurable through envVarGroups, otherwise it would be a good way to share the parameters cleanly to the other services without repeating a lot of env vars.
---

### How to Verify the Cluster is Working

1. **Check Service Health on Render**
   - Ensure all services show as "Running" in the Render dashboard.
   - No service should be in a crash loop or pending state.

2. **Temporal UI**
   - Access the Temporal UI at the provided endpoint (see `temporal-ui` service).
   - Log in and verify you can see namespaces, workflows, and cluster health.
   - If Worker is setup with Deployment Configuration, you can see the worker in the Deployments page (name not showing in the UI though ?)

3. **Database Connectivity**
   - Confirm that the `temporal-core` database is accessible and populated with Temporal tables. Can be done from inside hosts.
   - Access tables to check if there are values inside the database.
   - Confirm ES visibility index is setup with curl requests, same, can be done from inside hosts
   - After setting up some workflows, you can run counts to check if the index is receiving data.

4. **Elasticsearch**
   - Check that the Elasticsearch service is running and reachable from Temporal services.

5. **Logs**
   - Review logs for each service in Render for errors or warnings.

---

### Common Troubleshooting Steps

- **Service Fails to Start**
  - Check environment variables, ensure they are properly named and aligned with variables in the temporal config template, especially database and Elasticsearch connection details => sometimes it seems render doesn't sync automatically some variables. Ensure the config template of 
  - Ensure dependent services (e.g., database, Elasticsearch) are running and healthy.

- **Database Connection Errors**
  - Verify `temporal-core` is accessible from the service region.
  - Check PG Bouncer configuration and credentials.

- **Elasticsearch Issues**
  - Ensure the password is correctly passed to all Temporal services.
  - Check disk space and memory limits.

- **Temporal UI Not Loading**
  - Confirm the UI service is running and the correct port is exposed.
  - Check that the frontend service is reachable from the UI.
  - Ensure PORT env variable is aligned with the port you want to expose, render scans for the port specified on this env var.

- **Workflow Failures**
  - Review logs for the worker and history services for stack traces or configuration errors.

---

### Assumptions and Trade-offs

- **Assumptions**
  - All services are deployed in the same region for low latency.
  - Render automatically blocks non-internal communication to private services. Databases communications were authorized from public IPs for developpement, and blocked after initial setup.

- **Trade-offs**
  - Using the free plan for PostgreSQL and standard plan for Elasticsearch may limit scalability and performance.
  - ES is deployed in single-node mode but should be deployed on cluster mode.

### Deliverables

- render.yaml file in this repository
- live temporal UI : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows

## Part 2 - Python Temporal Workflows

### 1 - Orchestration

Example execution : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/72992716-3647-4c94-a639-a98ca8bbfd8d/019984fa-76c7-716d-9eef-6ae588d77835/history

Workflow that coordinates mutltiple workflows.
Execute addition, then multiplication in parallel of numbers, then synchronize all the outputs and sums the resulsts.
We also perform simple typing validation with pydantics.

### 2 - 

Example execution : 

Simulated failure of activity with retries fallback result : 
https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/c91a41df-eac1-44ea-a8a1-6facf20ac31d/01998525-2a31-7206-9c6c-fd0d29ce56ef/history

Success : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/c91a41df-eac1-44ea-a8a1-6facf20ac31d/01998530-2dc6-7bb9-a524-4b8e93ca5a0e/history

Failure of activity due to timeout but succeed because in bounds of maximum timeout  : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/75488f21-5248-4242-9519-fcbd7c71cc00/01998536-682b-77d6-9481-625c185f2293/history

Failure of activity due to timeout and fallback : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/9426f56a-c708-4bae-98cc-4dad69cf5e23/01998547-79f9-7683-946a-6511529e4415/history

This demonstrate capability to adapt error handling based on the type of error instead of catching everything.



