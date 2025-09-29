PYTHON ?= python3

.PHONY: test


helm-dev:
	./dev/install.sh
	MINIKUBE_STATUS=$$(minikube status)
	MINIKUBE_STOPPED_PATTERN="Stopped|not found"
	@if [ $$MINIKUBE_STATUS =~ $$MINIKUBE_STOPPED_PATTERN ];then\
		echo "Starting minikube"\
		minikube start;\
	else\
		echo "Minikube already running";\
	fi
	eval $$(minikube -p minikube docker-env)
	docker build -t python-worker:latest -f ./temporal-workflows/Dockerfile .
	helm install temporal-stack ./dev/temporal-stack
	kubectl wait --for=condition=available --timeout=60s deployment/temporal-ui
	kubectl port-forward svc/temporal-ui 5000:8080
	echo "Temporal UI should be available at http://localhost:5000"

argocd-setup:

	kubectl create namespace argocd || echo "argocd namespace already exists, continuing..."
	kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@if ! [ -x "$$(command -v argocd)" ]; then \
			curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64; \
			sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd; \
			rm argocd-linux-amd64;\
	else \
		echo "argocd CLI already installed, skipping installation" ;\
	fi

	kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
	kubectl port-forward svc/argocd-server -n argocd 8080:443


restart-worker-pod:
	eval $$(minikube -p minikube docker-env)
	docker build -t python-worker:latest -f ./temporal-workflows/Dockerfile .
	docker kill $$(docker ps | grep "python worker.py" | cut -d " " -f 1)
	kubectl rollout restart deployment python-worker

test-install:
	pip install -r temporal-workflows/requirements.txt

test:
	PYTHONPATH=temporal-workflows/app $(PYTHON) -m pytest temporal-workflows/tests
