## Part 1 - Deployment

### Deployment Sequence and Rationale

1. **Provision Databases**
   - The `temporal-core` PostgreSQL database is created first, as all Temporal services depend on it for state storage.
   - **Elasticsearch**: Deployed for visibility features (search, advanced queries). The password is auto-generated and passed to dependent services.

2. **Start Supporting Services**
   - **PG Bouncer**: Launched to provide connection pooling for PostgreSQL, improving performance and reliability.

3. **Initialize databases**
   - When using the temporal service container, databases are not initialized with their appropriate schemas. You can deploy an admin-tools container and enter it or script the initialization of the databases.

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

Unfortunately, it seems that postgres database is not configurable through envVarGroups, otherwise it would be a good way to share the parameters cleanly to the other services.
---

### How to Verify the Cluster is Working

1. **Check Service Health on Render**
   - Ensure all services show as "Running" in the Render dashboard.
   - No service should be in a crash loop or pending state.

2. **Temporal UI**
   - Access the Temporal UI at the provided endpoint (see `temporal-ui` service).
   - Log in and verify you can see namespaces, workflows, and cluster health.

3. **Database Connectivity**
   - Confirm that the `temporal-core` database is accessible and populated with Temporal tables.
   - Access tables to check if there are values inside the database.

4. **Elasticsearch**
   - Check that the Elasticsearch service is running and reachable from Temporal services.

5. **Logs**
   - Review logs for each service in Render for errors or warnings.

---

### Common Troubleshooting Steps

- **Service Fails to Start**
  - Check environment variables, especially database and Elasticsearch connection details.
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

- **Workflow Failures**
  - Review logs for the worker and history services for stack traces or configuration errors.

---

### Assumptions and Trade-offs

- **Assumptions**
  - All services are deployed in the same region for low latency.
  - The free plan is used for the database, which may have performance or connection limits.
  - Render automatically blocks non-internal communication to private services. Databases communications were authorized from public IPs for developpement, and blocked after initial setup.

- **Trade-offs**
  - Using the free plan for PostgreSQL and standard plan for Elasticsearch may limit scalability and performance.
