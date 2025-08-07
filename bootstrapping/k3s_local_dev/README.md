
[main index](../../README.md) | [bootstrap menu](../README.md)

<hr />

# Bootstrapping K3s on a Single Host on a Private LAN

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

## Component Project Pages and Further Information

| Component | URLs |
|---|---|
| `k3s` | [home](https://k3s.io/) and [GitHub](https://github.com/k3s-io/k3s/) |
| `NFS` Storage Provider | [GitHub](https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner) |
| `cert-manager` | [home](https://cert-manager.io/) and [documentation](https://cert-manager.io/docs/) and [GitHub Repository Index](https://github.com/cert-manager) |
| `Nginx` Gateway Fabrix | [documentation](https://docs.nginx.com/nginx-gateway-fabric/) and [GitHub](https://github.com/nginx/nginx-gateway-fabric) |
| `ArgoCD` | [home](https://argoproj.github.io/cd/) and [documentation](https://argo-cd.readthedocs.io/en/stable/) and [GitHub](https://github.com/argoproj/argo-cd) |
| `Tekton` | [home](https://tekton.dev/) and [documentation](https://tekton.dev/docs/) and [GitHub Repository Index](https://github.com/tektoncd) |
| `Gitea` | [home](https://about.gitea.com/) and [documentation](https://docs.gitea.com/) |
| `kube-prometheus` | [home](https://prometheus-operator.dev/) and [GitHub](https://github.com/prometheus-operator/kube-prometheus) |
| `BotKube` | [home](https://botkube.io/) and [documentation](https://docs.botkube.io/) |
| `keptn` | [home](https://keptn.sh/stable/) and [documentation](https://keptn.sh/stable/docs/) and [GitHub](https://github.com/keptn/lifecycle-toolkit)

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
| `podman` | OS Package is sufficient. You can use Docker if you really want to, but the world has moved on... |
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

<hr />

[main index](../../README.md) | [bootstrap menu](../README.md)
