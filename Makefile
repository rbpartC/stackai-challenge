PYTHON ?= python3

.PHONY: test


	

argocd-setup:
	kubectl create namespace argocd
	kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

	curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
	sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
	rm argocd-linux-amd64
	kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
	kubectl port-forward svc/argocd-server -n argocd 8080:443
	kubectl config set-context --current --namespace=argocd


restart-worker-pod:
	eval $$(minikube -p minikube docker-env)
	docker build -t python-worker:latest -f ./temporal-workflows/Dockerfile .
	docker kill $$(docker ps | grep "python worker.py" | cut -d " " -f 1)
	kubectl rollout restart deployment python-worker

test-install:
	pip install -r temporal-workflows/requirements.txt

test:
	PYTHONPATH=temporal-workflows/app $(PYTHON) -m pytest temporal-workflows/tests
