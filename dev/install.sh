#! /bin/bash

# run only if kubectl is not installed
if command -v kubectl &> /dev/null
then
    echo "kubectl is already installed"
else
    echo "kubectl is not installed, installing..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

    # Validate the binary (optional)
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl.sha256"
    echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check

    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
fi


if command -v helm &> /dev/null
then
    echo "helm is already installed"
else
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh
fi

if command -v minikube &> /dev/null
then
    echo "minikube is already installed"
else
    curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
    sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
fi



rm -f kubectl kubectl.sha256 get_helm.sh minikube-linux-amd64
