[main index](../README.md) | back to: [persisted volumes topic index](./README.md)

# Creating an NFS Server via a container for use by a Kubernetes Cluster

> [!WARNING]
> The below steps including running a container image with the `--privileged` parameter which is a HIGH SECURITY RISK. It is intended to use short term for local testing of persisted volumes. It is highly recommended that you stop and delete the container after you conclude your own experiments. 
> 
> _**DO NOT**_ expose the cluster or the NFS server to the outside world (aka "the Internet") !!!
>
> USE AT YOUR OWN RISK

Steps to be performed on a system that must host the NFS server:

```shell
# Prepare a data directory (example):
mkdir data
export NFS_DATA_PATH=$PWD/data

# NOTE: The data directory to be exported is in the environment variable NFS_DATA_PATH
#       Also, using podman requires "sudo" as the container needs to run privileged.

# Run the container - listen only on port 1049 (required for Ubuntu Server, else clients on the local net cannot connect to it)
sudo podman run -d --name nfs --privileged -v $NFS_DATA_PATH:/nfsshare -e SHARED_DIRECTORY=/nfsshare -p 1049:2049 docker.io/itsthenetwork/nfs-server-alpine:latest

# Forward port 2049/tcp to the NFS server (required for Ubuntu Server)
nohup socat tcp-l:2049,fork,reuseaddr tcp:127.0.0.1:1049 &
```

Clients can mount with:

```shell
mkdir -p $PWD/mnt/nfs
sudo mount -v -o vers=4,loud NFS_SERVER_NAME_OR_IP_ADDRESS:/ $PWD/mnt/nfs
```

# Prepare NFS Driver for microk8s

Follow instructions on https://microk8s.io/docs/how-to-nfs

For examples in this repo, the following commands were executed:

```shell
microk8s enable helm3
microk8s helm3 repo add csi-driver-nfs https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts
microk8s helm3 repo update
microk8s helm3 install csi-driver-nfs csi-driver-nfs/csi-driver-nfs \
    --namespace kube-system \
    --set kubeletDir=/var/snap/microk8s/common/var/lib/kubelet
```

<hr />

[main index](../README.md) | back to: [persisted volumes topic index](./README.md)