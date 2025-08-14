[main index](../../README.md) | [bootstrap menu](../README.md)

<hr />

# Bootstrapping K3s on a Single Host on a Private LAN

<!-- toc -->

  * [Basic Setup](#basic-setup)
- [Component Project Pages and Further Information](#component-project-pages-and-further-information)
- [Minimum Requirements](#minimum-requirements)
  * [Pre-installed Software Required](#pre-installed-software-required)
  * [Other software not technically required, but still useful](#other-software-not-technically-required-but-still-useful)
- [Approach](#approach)
- [Preparation](#preparation)
- [Installing K3s From Scratch](#installing-k3s-from-scratch)
- [Connectivity to the Cluster Gateway](#connectivity-to-the-cluster-gateway)
- [Get ArgoCD Admin Password](#get-argocd-admin-password)
- [Known Issues and/or Limitations](#known-issues-andor-limitations)
  * [Lets-Encrypt Limits](#lets-encrypt-limits)
  * [Kube-Prometheus and the Gateway Routes](#kube-prometheus-and-the-gateway-routes)
  * [Gitea DB Persistence](#gitea-db-persistence)
  * [Gitea SSH Access](#gitea-ssh-access)
- [More References and Further Reading](#more-references-and-further-reading)

<!-- tocstop -->

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
| `Gitea` | [home](https://about.gitea.com/) and [Helm Documentation](https://gitea.com/gitea/helm-gitea) and [documentation](https://docs.gitea.com/) |
| `kube-prometheus` | [home](https://prometheus-operator.dev/) and [GitHub](https://github.com/prometheus-operator/kube-prometheus) |
| `BotKube` | [home](https://botkube.io/) and [documentation](https://docs.botkube.io/) |
| `keptn` | [home](https://keptn.sh/stable/) and [documentation](https://keptn.sh/stable/docs/) and [GitHub](https://github.com/keptn/lifecycle-toolkit) |

> [!NOTE]
> For now, the `BotKube` and `keptn` installations is not included - may come at a later stage.

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
# The default below is for ALL end-points:
#   tekton
#   argocd
#   grafana
#   prometheus
#   alert-manager
#   gitea
export ROUTES=tekton,tekton-pipelines,tekton-dashboard,9097:argocd,argocd,argocd-server,80:grafana,kube-prometheus,kube-prometheus-grafana,80:prometheus,kube-prometheus,kube-prometheus-kube-prome-prometheus,9090:alert-manager,kube-prometheus,kube-prometheus-kube-prome-alertmanager,9093:gitea:devops:gitea-http:3000
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

A script is provided that now automates the entire bootstrap process.

Run it with the following command:

```bash
bootstrapping/k3s_local_dev/01_k3s_clean_start.sh
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

## Known Issues and/or Limitations

### Lets-Encrypt Limits

Lets-encrypt enforces a limit of "_5 certificates ... per exact same set of identifiers every 7 days_" ([reference](https://letsencrypt.org/docs/rate-limits/#new-certificates-per-exact-set-of-identifiers)). This is 1 certificate every 34 hours.

As per the current configuration of the stack, the deployment should therefore not be done more than 5x times in a week.

A typical error in the Kubernetes events may look like the following:

```bash
kubectl describe certificate/wildcard-toetzen-nl-certificate -n nginx-gateway
# Example Events Section:
# -----------------------
# Events:
#   Type     Reason     Age    From                                       Message
#   ----     ------     ----   ----                                       -------
#   Normal   Issuing    9m15s  cert-manager-certificates-trigger          Issuing certificate as Secret does not exist
#   Normal   Generated  9m15s  cert-manager-certificates-key-manager      Stored new private key in temporary Secret resource "wildcard-toetzen-nl-certificate-v5cgv"
#   Normal   Requested  9m15s  cert-manager-certificates-request-manager  Created new CertificateRequest resource "wildcard-toetzen-nl-certificate-1"
#   Warning  Failed     9m9s   cert-manager-certificates-issuing          The certificate request has failed to complete and will be retried: Failed to wait for order resource "wildcard-example-tld-certificate-1-1111111111" to become ready: order is in "errored" state: Failed to create Order: 429 urn:ietf:params:acme:error:rateLimited: too many certificates (5) already issued for this exact set of identifiers in the last 168h0m0s, retry after 2025-08-12 14:36:55 UTC: see https://letsencrypt.org/docs/rate-limits/#new-certificates-per-exact-set-of-identifiers

```

Once the limit is reached, take note of the `retry after` hint.

> [!IMPORTANT]
> If the certificate creation fails, the pipeline will continue, but will skip installing `Gateway`, `HTTPRoute` and related resources dependant on the certificates. I did this of personal preference, as I value working with minimal interruption more than just not being able to proceed because a cluster cannot be provisioned. It is slightly more inconvenient, but definitely not a show stopper and after a fresh run of the installation after a couple of days the problem should go away anyway.

### Kube-Prometheus and the Gateway Routes

As of 12 August 2025, the `Gateway` configuration option in the Helm chart was still marked as very "experimental" and should not considered be stable. As a result, the `HTTPRoute` objects is still created separately. This will hopefully soon change to the point where the Helm chart values can be set to provision the various routes.

### Gitea DB Persistence

There is currently no option to set the persistent volume for the built-in database options (`postgres-ha` and`postgres`).

In the near future I would likely update this stack to include a stand-alone database with persistence.

I also need to create `PersistentVolume` objects in order to re-use the previous the same volumes every time the cluster is re-created.

An example manifest (just as reference for later):

```yaml
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: nfs-pv-existing-data
spec:
  capacity:
    storage: 10Gi # This should match the size of your existing data directory
  volumeMode: Filesystem
  accessModes:
    - ReadWriteMany # Adjust this to match your use case
  persistentVolumeReclaimPolicy: Retain # IMPORTANT: This prevents data loss on PV deletion
  storageClassName: manual
  nfs:
    path: /path/to/nfs/share/long-random-name # <--- SET THIS TO YOUR EXISTING DIRECTORY
    server: 192.168.1.100                    # <--- SET THIS TO YOUR NFS SERVER IP/HOSTNAME
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc-for-existing-data
spec:
  accessModes:
    - ReadWriteMany # Must match the PV
  storageClassName: manual # Must match the PV
  resources:
    requests:
      storage: 10Gi # Must match the PV
```

### Gitea SSH Access

The `TLSRoute` implementation is not yet stable, and therefore any SSH access to Gitea would require a port-forwarding session.

Example:

```bash
kubectl port-forward service/gitea-ssh --address 0.0.0.0 -n devops 9022:22
```

Then, in your `~/.ssh/config` you can add the following:

```text
Host gitea-k3s
    HostName localhost
    Port 9022
    IdentityFile /home/your-username/.ssh/your-private-key
    IdentitiesOnly yes
```

And then, to clone a repository, you would run something like this:

```bash
git clone git@gitea-k3s:username/project-name.git
```

## More References and Further Reading

* [Tekton `TaskRun` Examples](https://github.com/tektoncd/pipeline/tree/release-v1.1.x/examples/v1/taskruns)

<hr />

[main index](../../README.md) | [bootstrap menu](../README.md)
