# StackAI Challenge

A full-stack Temporal deployment with Python LLM workflows, Helm, and Render.com integration.

## Table of Contents
- [Project Structure](#project-structure)
- [Deliverables](#deliverables)
- [Quick Start](#quick-start)
- [Getting Started](#getting-started)
- [Deployment Details](#deployment-details)
- [Workflow Examples](#workflow-examples)
- [Development Environment](#development-environment)
- [Troubleshooting](#troubleshooting)
- [Assumptions and Trade-offs](#assumptions-and-trade-offs)

## Project Structure

This repository is organized so that each main folder contains the code and Dockerfile to build a Docker image used by one or more services in the deployment:

- `/server` - Contains the Temporal server configuration, entrypoints, and Dockerfile. The image built here is used for all core Temporal services (frontend, history, matching, worker, admin-tools).
- `/web` - Contains the Temporal UI code and Dockerfile. The image built here is used for the Temporal UI web service.
- `/temporal-workflows` - Contains the Python Temporal worker code and Dockerfile. The image built here is used for the custom Python worker service.
- `/config` - Contains configuration files (YAML) for Temporal and related services. These are copied into the appropriate images at build time.
- `/dev/temporal-stack` - Contains the Helm chart for local Kubernetes deployment, referencing the images built from the above folders.
- `render.yaml` - Render.com deployment configuration, referencing the images and environment variables for all services.
- `.pre-commit-config.yaml` - Precommit config to ensure homogenous styling and enforce compliance when collaborating.
- `.github/workflows/` - Simple CI job to ensure pre-commit / linting are properly applied to maintain quality

Each service in the deployment uses the Docker image built from its corresponding folder, ensuring clear separation of concerns and easy customization or extension of any component.

## Deliverables
- [x] `render.yaml` file ([link](https://github.com/rbpartC/stackai-challenge/blob/master/render.yaml))
- [x] Live Temporal UI ([link](https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows))
- [x] Example workflow runs (see  Part 2 - Python Temporal Workflows)
- [x] Helm chart  ([link](https://github.com/rbpartC/stackai-challenge/blob/master/dev/temporal-stack))
- [x] ArgoCD deployment  ([link](https://github.com/rbpartC/stackai-challenge/blob/master/dev/argocd-application.yaml))


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

```bash
./temporal-sql-tool --ep $POSTGRES_SEEDS -p $POSTGRES_PORT -u $POSTGRES_USER --pw $POSTGRES_PASSWORD --db $DBNAME --pl postgres12 --tls setup-schema -d schema/postgresql/v12/temporal/versioned
```

      Commands to run inside admin-tools container to put ES settings and setup visibility mapping/index

```bash
ES_SERVER="${ES_SCHEME}://${ES_SEEDS%%,*}:${ES_PORT}"
SETTINGS_URL="${ES_SERVER}/_cluster/settings"
SETTINGS_FILE=${TEMPORAL_HOME}/schema/elasticsearch/visibility/cluster_settings_${ES_VERSION}.json
SCHEMA_FILE=${TEMPORAL_HOME}/schema/elasticsearch/visibility/index_template_${ES_VERSION}.json
TEMPLATE_URL="${ES_SERVER}/_template/temporal_visibility_v1_template"
INDEX_URL="${ES_SERVER}/temporal_visibility_v1_dev"
curl --fail --user "${ELASTIC_USERNAME}":"${ELASTIC_PASSWORD}" -X PUT "${SETTINGS_URL}" -H "Content-Type: application/json" --data-binary "@${SETTINGS_FILE}" --write-out "\n"
curl --fail --user "${ELASTIC_USERNAME}":"${ELASTIC_PASSWORD}" -X PUT "${TEMPLATE_URL}" -H 'Content-Type: application/json' --data-binary "@${SCHEMA_FILE}" --write-out "\n"
curl --user "${ELASTIC_USERNAME}":"${ELASTIC_PASSWORD}" -X PUT "${INDEX_URL}" --write-out "\n"
```
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

## Part 2 - Python Temporal Workflows

### Basic examples

First examples to demonstrate understanding of the patterns

#### 1 - Orchestration

Example execution : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/f6e515a6-4b71-46b8-ac38-40c362a4f4ad/01998f5b-81ef-70e2-926c-1e3e50828567/history 

Workflow that coordinates mutltiple workflows.
Execute addition, then multiplication in parallel of numbers, then synchronize all the outputs and sums the resulsts.
We also perform simple typing validation with pydantics.

#### 2 - Async Operations

Example execution : 

Simulated failure of activity: 
https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/f6e515a6-4b71-46b8-ac38-40c362a4f4ad/01998f5c-6004-7ec4-a3c4-44a2dec9c2d4/history

Success : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/f6e515a6-4b71-46b8-ac38-40c362a4f4ad/01998f5c-4960-7c65-b926-cb07a60db893/history

Failure of activity due to timeout and fallback : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/f6e515a6-4b71-46b8-ac38-40c362a4f4ad/01998f5d-5c8e-7ca8-b9f4-07c412612e94/history

This demonstrate capability to adapt error handling based on the type of error instead of catching everything.

#### 3 - Fire and foregt 

Example execution :

Firing workflow : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/ad46e0f2-7a69-4c39-a30e-fe10be906c1b/01998f5f-c0e1-7a00-86e7-c4aa4f20f75a/history

Forgetted workflow : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/2f57abc6-2000-48a0-a893-4f8469ea854a/01998f5f-c149-7c24-9323-4db6ba06e918/history

#### 4 - Long Running Processes

Initial workflow : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/126bcaef-49f8-4488-9695-bb4ab5b3d503/01998f6d-f1e5-75be-9c21-e8648bbaf3dc/history

Continued as new :
https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/126bcaef-49f8-4488-9695-bb4ab5b3d503/5ad42d87-ac9b-4334-aba3-27b9ac011430/history

Completion : 
https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/126bcaef-49f8-4488-9695-bb4ab5b3d503/c205b2e4-948a-433d-9565-52d93d6bf298/history

### Advanced use case

We now build a system more advanced that features usage of LLMs

The workflow WebPageReviewWorkflow demonstrate orchestration techniques, with a first activity to extract textual data from a webpage, then (sequentially) we launch parallel execution of LLMs activities (entity extraction, summarization, classification). We then wait for a "human review" signal (with timeout and automatic validation) that must be given through the UI before completing the workflow.

Here is an example run : 
https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/f912d5d9-c60b-4f7b-bda4-b11244028fd0/01998f59-6430-773a-bd2b-6cdf4999c226/history


If you want first to identify links of interest to you, you can also run the ExtractLinksWorkflows, where you provide a tag and a date to search for articles up to a certain point in Medium Archives.
For example, if I want to list articles with the "technology" tag : 
Start run : https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/310539fb-5a88-490f-b301-f26e44a64d49/01998fe4-bef4-7974-92ff-babfc9a06aa4/history
Last run : 
https://temporal-ui-oq8v.onrender.com/namespaces/default/workflows/310539fb-5a88-490f-b301-f26e44a64d49/3ccbea48-fa57-45df-b625-a3532526d53d/history

## Part 3 - Development Environment Setup

### 1. Install tools

Run ./dev/install.sh script to install automatically kubectl, helm, minikube on Linux/Debian machine.
It detects automatically which tools needs to be installed.

### 2. Setup

First start your local cluster

```bash
minikube start
```

You **must** build at least once the docker image with the python workflows **inside the docker env of k8s** for local development.
Running from the root of this repo:

```bash
eval $(minikube -p minikube docker-env)
docker build -t python-worker:latest -f ./temporal-workflows/Dockerfile .
```

Then deploy the helm chart by running:

```bash
helm install temporal-stack ./dev/temporal-stack
```

To view the UI on your computer, forward port

```bash
kubectl port-forward svc/temporal-ui 8080:8080
```

You can now run workflows directly on your computer on http://localhost:8080/


### 3. ArgoCD

#### 1. Setup

Configure and install argocd locally. Everything was packaged into a make command for simplicity (install with sudo apt-get install build-essential on linux/debian)

```bash
make setup
```

Then, once your forwarded port to 8080 on your host machine you can login through the CLI to create the temporal app very easily.

```bash
argocd login 127.0.0.1:8080 --username admin --password $(argocd admin initial-password -n argocd | head -n 1)

argocd cluster add minikube

kubectl apply -f $(pwd)/dev/argocd-application.yaml -n argocd
```

With the current setup, the containers will be create in default namespace.
To view Temporal UI at the same time, forward the container port to a different port than ArgoCD, like:

```bash
kubectl port-forward -n default svc/temporal-ui 5000:8080
```

#### 2. Development cycle

Once your setup is done, you can edit the python workflows and refresh the python worker with another custom make command for simplicity and ease of use.

```bash
make restart-worker-pod
```

The pod will restart with the new image you just built (and you kill the previous one to insure you don't run outdated code), so you can run instantly the new workflow in your local UI


#### 3. Testing before containerize

You can also run the local test suite that should be enough to ensure scripts are not broken.
Run the installation of python dependencies (WARNING : you should probably setup a virtual environment before running install)

```bash
make install
```

Then simply execute the tests like so

```bash
make test
```