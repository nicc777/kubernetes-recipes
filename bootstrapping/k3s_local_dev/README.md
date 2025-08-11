
[main index](../../README.md) | [bootstrap menu](../README.md)

<hr />

# Bootstrapping K3s on a Single Host on a Private LAN

> [!INFO]
> The process still needs to be streamlined, and therefore the current documented process may appear more manual than _Infrastructure-as-Code_ for now.

On this page are instructions to setup the following components on a system hosted on a private LAN:

| Component | Use Case |
|---|---|
| `K3s` | Kubernetes Distribution |
| NFS | Persistent storage |
| `cert-manager` | certificate management |
| `Nginx` Gateway Fabric | Ingress |
| `ArgoCD` | Deployment Orchestration |
| `Tekton` | Running pipelines in cluster |
| `Gitea` | In-cluster ArgoCD integration |
| `kube-prometheus` | Observability |
| `Botkube` | Messaging about cluster events in Slack |
| `keptn` | DevOps monitoring|

### Basic Setup

The recipe assumes the following basic setup:

![basic setup](./k3_local_dev_design-Basic_Concept.png)

Some variations can be tollerated, notably that the target server and developer laptop may also be one and the same system.

## Component Project Pages and Further Information

| Component | URLs |
|---|---|
| `k3s` | [home](https://k3s.io/) and [GitHub](https://github.com/k3s-io/k3s/) |
| `NFS` Storage Provider | [GitHub](https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner) |
| `cert-manager` | [home](https://cert-manager.io/) and [documentation](https://cert-manager.io/docs/) and [GitHub Repository Index](https://github.com/cert-manager) |
| `Nginx` Gateway Fabrix | [documentation](https://docs.nginx.com/nginx-gateway-fabric/) and [GitHub](https://github.com/nginx/nginx-gateway-fabric) |
| `ArgoCD` | [home](https://argoproj.github.io/cd/) and [documentation](https://argo-cd.readthedocs.io/en/stable/) and [GitHub](https://github.com/argoproj/argo-cd) |
| `Tekton` | [home](https://tekton.dev/) and [documentation](https://tekton.dev/docs/) and [GitHub Repository Index](https://github.com/tektoncd) and [Operator Installation Instruction](https://github.com/tektoncd/operator/blob/main/docs/install.md) |
| `Gitea` | [home](https://about.gitea.com/) and [documentation](https://docs.gitea.com/) |
| `kube-prometheus` | [home](https://prometheus-operator.dev/) and [GitHub](https://github.com/prometheus-operator/kube-prometheus) |
| `BotKube` | [home](https://botkube.io/) and [documentation](https://docs.botkube.io/) |
| `keptn` | [home](https://keptn.sh/stable/) and [documentation](https://keptn.sh/stable/docs/) and [GitHub](https://github.com/keptn/lifecycle-toolkit) |

## Minimum Requirements

You will need to meet all of these requirements for this recipe to be useful to you if you want to practically implement it yourself:

| Requirement | Guidance |
|---|---|
| Hardware System Specification | A system with sufficient cores and threads (8/16 recommended) and at least 32 GiB RAM and at least 100 GiB available storage capacity |
| Operating System | A fairly recent version of a Linux distribution that you are comfortable with. This document assumes a Debian based system, but only really as it relates to package management. All other commands should be similar on all Linux distributions. Some file locations may be different. |
| NFS Server | For actually using persistant storage. The NFS server could also run on the same base host as K3s, but no assumptions are made on this |
| `BASH` shell | All scripts assume `bash` is installed. In terms of the user (you), no assumptions are made on the shell you may use. |
| Software | See below for the software required. Your distribution may offer some of these in it's package manager, but for some it is better to install from the software provided releases. |
| A public domain you own | The examples assume you own a domain that can be used with `cert-manager` and `lets-encrypt` to generate TLS certificates. The examples focus on Route 53, since this is what I use, but regardless, try to pick a registrar that is well supported by `lets-encrypt` and also `cert-manager`. |
| Root access on the server that will host `K3s` | Goes without saying, but you need `root` access from time to time. |
| A private OCI compliant registry (cloud or local hosted) | `Zot` is a really good option for a self-hosted private registry. [GitHub](https://github.com/project-zot/zot) and [Installation Documentation](https://zotregistry.dev/v2.1.7/install-guides/install-guide-linux/) |

### Pre-installed Software Required

The examples make extensive use of the following tools and it is assumed you have them installed and are already at least somewhat familiar with their usage:

| Software Package | Installation Guidance |
|---|---|
| `bash` | OS Package is sufficient |
| `curl` | OS Package is sufficient |
| `git` command line client | OS Package is sufficient |
| `sed` command line client | OS Package is sufficient |
| `podman` | OS Package is sufficient. You can use Docker if you really want to, but the world has moved on... |
| `helm` | Follow the instructions from the [Helm Documentation](https://helm.sh/docs/intro/install/) |
| `kubectl` | Install a version closely versioned to your Kubernetes version (plus-or-minus 1 version should be ok). [Linux Installation Instructions](https://v1-32.docs.kubernetes.io/docs/tasks/tools/install-kubectl-linux/) |
| Text Editor like `neovim` | Something you are familiar with that you can use to edit files in the terminal with. I prefer [`Lazyvim`](https://www.lazyvim.org/), but it does not really matter what you use. |

### Other software not technically required, but still useful

| Software Package | Installation Guidance |
|---|---|
| `kubectx` | Quick context and namespacew switcher for using with `kubectl` and related tools. [Repository with Installation Instructions](https://github.com/ahmetb/kubectx) |
| `k9s` | Really handy tool for looking at resources in Kubernetes. [Installation Instructions](https://k9scli.io/topics/install/) and [Latest Releases](https://github.com/derailed/k9s/releases) |
| `socat` | A handy networking tool. The OS provided packages should be sufficient. |

## Approach

The Cluster will be installed on a host as a single-node cluster. Thereafter, `Tekton` will be installed, from where the remainder of the installation and configuration will be run through pipelines.

The idea is to adopt DevOps / DevSecOps best practices as early as possible.

## Preparation

Create an environment file that you can use to set all the variable values used in this recipe:

```bash
cat <<EOF > $HOME/.k3s_local_dev_env
# Add you private server LAN IP address here:
export SERVER=...

# Add your AWS credentials here for lets-encrypt to update your Route 53 ZONE:
export LE_R53_KEY=...
export LE_R53_SECRET=...

# Add your domain information below:
export ROUTE_53_ZONEID=...
export ROUTE_53_DOMAIN=...
# Below must be a string suitable for Kubenetes object names. 
export ROUTE_53_RESOURCE_ID=$(echo ${ROUTE_53_DOMAIN} | sed "s/\./\-/g")

# Your Kubernetes configuration for using kubectl and other tools:
export KUBECONFIG=$HOME/k3s.yaml

# NFS Server Configuration 
export NFS_SERVER=...
export NFS_PATH=...

# Other
export EMAIL=...

# DNS Record names to create routes for - comma separated list:
# FORMAT: SET OF record_name,target_namespace,service_name,port
# RECORD SET seprator is a colon (:)
# 2x Record Set Example: export ROUTES=tekton,tekton-pipelines,tekton-dashboard,9097:argocd,argocd,argocd-server,80
export ROUTES=tekton,tekton-pipelines,tekton-dashboard,9097
EOF

chmod 600 $HOME/.k3s_local_dev_env

# Load the file:
. $HOME/.k3s_local_dev_env
```

> [!IMPORTANT]
> This file contains sensitive information, and should be protected against unauthorized access. DO NOT make this file public in any way !!!

On the server you also need to ensure your user can run certain commands with `sudo` and not require a password. Add the following to your `sudoers` file:

```text
your-user-name ALL = NOPASSWD: /usr/local/bin/k3s-uninstall.sh
your-user-name ALL = NOPASSWD: /tmp/k3s_install.sh
your-user-name ALL = NOPASSWD: /tmp/web-forward-into-k3s.sh
```

## Installing K3s From Scratch

I like to run a clean version in my local environment for experiments. This approach holds certain advantages, including:

* Forces automation via pipelines
* Ensures all steps can be easily reproduced via pipelines
* Keeping pace with new versions of key software elements and enables early identification of breaking changes that can be quickly fixed in pipelines, ensuring you always have the latest working configuration for a local development and testing environment.
* Experiments are easily reproducible

### Uninstall Any Previous K3s Installation

Only required if you have a current `k3s` cluster.

Also refer to the [k3s documentation](https://docs.k3s.io/installation/uninstall) for the most up to date information.

Command:

```bash
ssh $SERVER /usr/local/bin/k3s-uninstall.sh
```

### Install a Fresh Cluster

> [!NOTE]
> First ensure the previous cluster is uninstalled - see previous section

This specific installation will do the following:

* Disable the default Ingress controller that ships with K3s (`Traefik`).
* Force `NodePorts` to listen on the Host network enabling us to more easily configure port forwarding from the Host to the cluster ingress points.

Commands:

```bash
cat <<EOF > /tmp/k3s_install.sh
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server" sh -s - --disable=traefik --kubelet-arg="node-ip=0.0.0.0"
sudo cp -vf /etc/rancher/k3s/k3s.yaml /tmp/k3s.yaml
sudo chown $USER:$USER /tmp/k3s.yaml
EOF

scp /tmp/k3s_install.sh $SERVER:/tmp/

ssh $SERVER "chmod 700 /tmp/k3s_install.sh && sudo /tmp/k3s_install.sh"
```

On any other system you need the `KUBECONFIG`, run:

```bash
# [OPTIONAL] Only required if your Kubernetes cluster
#            is not running on your local machine

scp $SERVER:/tmp/k3s.yaml ~/

sed -i "s/127.0.0.1/${SERVER}/g" $HOME/k3s.yaml
```

> [!NOTE]
> Once the `k3s.yaml` is copied, you need to update the IP address of the server in the file

Quick test:

```bash
kubectl get namespaces
# Expected Output:
# ----------------------------------------
# default           Active   44s
# kube-node-lease   Active   44s
# kube-public       Active   44s
# kube-system       Active   44s
```

## Install `Tekton`

To install Tekton, run the following:

```bash
kubectl apply -f https://storage.googleapis.com/tekton-releases/operator/latest/release.yaml
sleep 60 
kubectl apply --filename https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml
sleep 60
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/latest/release.yaml
sleep 60
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/latest/interceptors.yaml
sleep 60
kubectl apply --filename https://storage.googleapis.com/tekton-releases/dashboard/latest/release-full.yaml
sleep 10
```

To test connectivity, temporarily setup a forwarding proxy:

```bash
kubectl port-forward service/tekton-dashboard --address 0.0.0.0 -n tekton-pipelines 9097:9097
```

And open a web browser from another terminal session:

```bash
open http://localhost:9097/

```

As a final step, also import the environment file as a secret for use by Tekton pipelines and tasks:

```bash
kubectl apply -f bootstrapping/k3s_local_dev/manifests/01_pipeline_administrative_clusterrole_for_tekton.yaml

cp -vf $HOME/.k3s_local_dev_env /tmp/task_env

sed -i "s/export //g" /tmp/task_env

kubectl create secret generic env-secret --from-env-file=/tmp/task_env -n development
```

### Testing and Validating the Installation

Apply the following two manifests:

```bash
kubectl apply -f bootstrapping/k3s_local_dev/manifests/02_test_taskrun.yaml
```

If you still have the web browser open on the Tekton dashboard, you should notice the following:

![dashboard 01](./01_taskrun_expected_result.png)

Another way to check is via the command line:

```bash
kubectl logs build-push-task-run-1-pod -n development
# Expected Output:
# ----------------------------------------
# Defaulted container "step-get-namespaces" out of: step-get-namespaces, prepare (init), place-scripts (init)
# Client Version: v1.33.3
# Kustomize Version: v5.6.0
# Server Version: v1.33.3+k3s1
# NAME                         STATUS   AGE
# default                      Active   4h44m
# development                  Active   62m
# kube-node-lease              Active   4h44m
# kube-public                  Active   4h44m
# kube-system                  Active   4h44m
# tekton-dashboard             Active   121m
# tekton-operator              Active   140m
# tekton-pipelines             Active   140m
# tekton-pipelines-resolvers   Active   127m
```

To cleanup the test:

```bash
# OPTIONAL...
kubectl delete -f bootstrapping/k3s_local_dev/manifests/02_test_taskrun.yaml
```

### Preparing the Bootstrapping Pipelines / Tasks

Next, we will prepare the bootstrapping namespace and resources to deploy the rest of the required services.

Start by running the following:

```bash
kubectl apply -f bootstrapping/tekton/tasks/k3s_local_development/01_bootstrapping_rbac.yaml

kubectl create secret generic env-secret --from-env-file=/tmp/task_env -n bootstrapping
```

## Run the Provisioning Pipeline

The rest of the bootstrap process is handled by Tekton.

You can open the Tekton Dashboard using the port-forwarder approach shown earlier. The DNS with the Gateway can be used after the bootstrap process is complete.

Run the following:

```bash
kubectl apply -f bootstrapping/tekton/tasks/k3s_local_development/02_provision_k3s_local.yaml
```

Check the status and ensure the `SUCCEEDED` column has the value `True`:

```bash
kubectl get pipelineruns -n bootstrapping
# Expected Output:
# ----------------------------------------
# NAME            SUCCEEDED   REASON      STARTTIME   COMPLETIONTIME
# bootstrap-run   True        Succeeded   7m12s       4m48s
```

## Connectivity to the Cluster Gateway

If you have not already done so before, also add the `socat` rule to forward all your HTTP and HTTPS traffic to the `Gatewway` `NodePort` end points:

```bash
cat <<EOF > /tmp/web-forward-into-k3s.sh
#!/usr/bin/env bash

nohup socat tcp-listen:80,fork tcp:192.168.2.13:30080 &
nohup socat tcp-listen:443,fork tcp:192.168.2.13:30443 &
EOF

scp /tmp/web-forward-into-k3s.sh $SERVER:/tmp

ssh $SERVER "chmod 700 /tmp/web-forward-into-k3s.sh && sudo /tmp/web-forward-into-k3s.sh"
```

## Get ArgoCD Admin Password

The admin password is available in the output of the tasks when you prefer to use the Tekton UI.

However, it is also easy and probably faster to just get the password from the terminal:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

<hr />

[main index](../../README.md) | [bootstrap menu](../README.md)
