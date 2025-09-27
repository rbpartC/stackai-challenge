## Project Structure

This repository is organized so that each main folder contains the code and Dockerfile to build a Docker image used by one or more services in the deployment:

- `/server` - Contains the Temporal server configuration, entrypoints, and Dockerfile. The image built here is used for all core Temporal services (frontend, history, matching, worker, admin-tools).
- `/web` - Contains the Temporal UI code and Dockerfile. The image built here is used for the Temporal UI web service.
- `/temporal-workflows` - Contains the Python Temporal worker code and Dockerfile. The image built here is used for the custom Python worker service.
- `/config` - Contains configuration files (YAML) for Temporal and related services. These are copied into the appropriate images at build time.
- `/dev/temporal-stack` - Contains the Helm chart for local Kubernetes deployment, referencing the images built from the above folders.
- `render.yaml` - Render.com deployment configuration, referencing the images and environment variables for all services.
- `.pre-commit-config.yaml` - Precommit config to ensure homogenous styling and enforce compliance when collaborating.

Each service in the deployment uses the Docker image built from its corresponding folder, ensuring clear separation of concerns and easy customization or extension of any component.



## Part 1 - Deployment

### Deployment Sequence and Rationale

1. **Provision Databases**
   - The `temporal-core` PostgreSQL database is created first, as all Temporal services depend on it for state storage.
   - **Elasticsearch**: Deployed for visibility features (search, advanced queries). The password is auto-generated and passed to dependent services.

2. **Start Supporting Services**
   - **PG Bouncer**: Launched to provide connection pooling for PostgreSQL, improving performance and reliability.

3. **Initialize databases**
   - When using the temporal service container (and not the autosetup one), databases are not initialized with their appropriate schemas. You can deploy an admin-tools container as worker and enter it, then run the commands with the temporal-sql-tool to setup the psql schemas, and run the commands to configure the ES cluster and put the schema template, and create the visibility index. This container can be suspended after setting-up/upgrading schemas. The auto-setup script is actually a good way to understand the sequence and which commands to run.
   
      Command to run inside admin-tools container to create the PSQL schema (version of the schema depends on the version of temporal; I used latest versions of everything for simplicity)
   `
   ./temporal-sql-tool --ep $POSTGRES_SEEDS -p $POSTGRES_PORT -u $POSTGRES_USER --pw $POSTGRES_PASSWORD --db $DBNAME --pl postgres12 --tls setup-schema -d schema/postgresql/v12/temporal/versioned
   `
      Commands to run inside admin-tools container to put ES settings and setup visibility mapping/index
   `
   ES_SERVER="${ES_SCHEME}://${ES_SEEDS%%,*}:${ES_PORT}"
   SETTINGS_URL="${ES_SERVER}/_cluster/settings"
   SETTINGS_FILE=${TEMPORAL_HOME}/schema/elasticsearch/visibility/cluster_settings_${ES_VERSION}.json
   SCHEMA_FILE=${TEMPORAL_HOME}/schema/elasticsearch/visibility/index_template_${ES_VERSION}.json
   TEMPLATE_URL="${ES_SERVER}/_template/temporal_visibility_v1_template"
   INDEX_URL="${ES_SERVER}/temporal_visibility_v1_dev"
   curl --fail --user "${ELASTIC_USERNAME}":"${ELASTIC_PASSWORD}" -X PUT "${SETTINGS_URL}" -H "Content-Type: application/json" --data-binary "@${SETTINGS_FILE}" --write-out "\n"
   curl --fail --user "${ELASTIC_USERNAME}":"${ELASTIC_PASSWORD}" -X PUT "${TEMPLATE_URL}" -H 'Content-Type: application/json' --data-binary "@${SCHEMA_FILE}" --write-out "\n"
   curl --user "${ELASTIC_USERNAME}":"${ELASTIC_PASSWORD}" -X PUT "${INDEX_URL}" --write-out "\n"
   `
   This step can be automated as demonstrated later with the local dev environment, but in production it wouldn't serve any purpose or could be even dangerous (table suppressions or incompatibilities could be generated), and this step is very fast anyway.

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
  - Check environment variables, ensure they are properly named and aligned with variables in the temporal config template, especially database and Elasticsearch connection details => sometimes it seems render doesn't sync automatically some variables on redeployment / variable changes. Ensure the config template of temporal uses the correct env variable names.
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

- **Workflow Failures or Not Starting**
  - Review logs for the worker and history services for stack traces or configuration errors.
  - Ensure versioning/deployement/buildId behavior doesn't cause worker to stop picking up tasks

---

### Assumptions and Trade-offs

- **Assumptions**
  - All services are deployed in the same region for low latency.
  - Render automatically blocks non-internal communication to private services. Databases communications were authorized from public IPs for developpement, and blocked after initial setup.

- **Trade-offs**
  - Using the free plan for PostgreSQL and standard plan for Elasticsearch may limit scalability and performance.
  - ES is deployed in single-node mode but should be deployed on cluster mode.

### Optionals 

- Enable archival for your namespace (default here) by logging into the shell of your temporal-frontend container, and run :

`
temporal operator namespace update --history-archival-state enabled -n default
temporal operator namespace update --visibility-archival-state enabled -n default
`

### Deliverables

- render.yaml file in this repository
- live temporal UI : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows

## Part 2 - Python Temporal Workflows

### 1 - Orchestration

Example execution : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/72992716-3647-4c94-a639-a98ca8bbfd8d/019984fa-76c7-716d-9eef-6ae588d77835/history

Workflow that coordinates mutltiple workflows.
Execute addition, then multiplication in parallel of numbers, then synchronize all the outputs and sums the resulsts.
We also perform simple typing validation with pydantics.

### 2 - Async Operations

Example execution : 

Simulated failure of activity with retries fallback result : 
https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/c91a41df-eac1-44ea-a8a1-6facf20ac31d/01998525-2a31-7206-9c6c-fd0d29ce56ef/history

Success : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/c91a41df-eac1-44ea-a8a1-6facf20ac31d/01998530-2dc6-7bb9-a524-4b8e93ca5a0e/history

Failure of activity due to timeout but succeed because in bounds of maximum timeout  : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/75488f21-5248-4242-9519-fcbd7c71cc00/01998536-682b-77d6-9481-625c185f2293/history

Failure of activity due to timeout and fallback : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/9426f56a-c708-4bae-98cc-4dad69cf5e23/01998547-79f9-7683-946a-6511529e4415/history

This demonstrate capability to adapt error handling based on the type of error instead of catching everything.


### 3 - Fire and foregt 

Example execution :

Firing workflow : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/90499a3b-71d7-4edd-8c6c-7a315b226693/01998562-5bb0-7604-9e2f-5639bd02b981/history

Forgetted workflow : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/34686d1a-e722-4885-8096-18d4cbb58ddb/01998562-5c60-7121-9d71-f32192d6db4c/history

### 4 - Long Running Processes

Initial workflow : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/0436499f-b538-46b1-b798-517f676beea4/01998573-eacf-7cb3-8dd8-061bdc7eb560/history

Continued as new 1 : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/0436499f-b538-46b1-b798-517f676beea4/bb14b72e-f110-45bb-977b-888a2d432b4d/history

Completion : 
https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/0436499f-b538-46b1-b798-517f676beea4/83951006-e91e-4f13-ad06-26e4553ac040/history

## Part 3 - Development Environment Setup

### 1. Install tools

Run ./dev/install.sh to install automatically kubectl, helm, minikube on Linux/Debian machine.
It detects automatically which tools needs to be installed.

### 2. Setup

First start your local cluster

minikube start

You **must** build at least once the docker image with the python workflows **inside the docker env of k8s** for local development.
Running from the root of this repo :

`
eval $(minikube -p minikube docker-env)
docker build -t python-worker:latest -f ./temporal-workflows/Dockerfile .
`

Then deploy the helm chart by running : 

`
helm install temporal-stack ./dev/temporal-stack
`

To view the UI on your computer, forward port
`
kubectl port-forward svc/temporal-ui 8080:8080
`

You can now run workflows directly on your computer on http://localhost:8080/


### 3. ArgoCD

#### 1. Setup

Configure and install argocd locally
`
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
rm argocd-linux-amd64
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
kubectl port-forward svc/argocd-server -n argocd 8080:443
kubectl config set-context --current --namespace=argocd

`

Then, once your forwarded port to 8080 on your host machine you can login through the CLI to create the temporal app very easily.

`
argocd login 127.0.0.1:8080 --username admin --password $(argocd admin initial-password -n argocd | head -n 1)

argocd cluster add minikube

kubectl apply -f /home/ruben/personal/stackai/dev/argocd-application.yaml -n argocd
`

With the current setup, the containers will be create in default namespace.
To view Temporal UI at the same time, forward the container port to a different port than ArgoCD, like : 

`
kubectl port-forward -n default svc/temporal-ui 5000:8080
`