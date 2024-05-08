[main index](../README.md) | back to: [persisted volumes topic index](./README.md)

# Static Web Site Example

This is an example of serving a static website from files on a NFS share.

# Prerequisites

* A NFS server (see [nfs-for-microk8s.md](./nfs-for-microk8s.md))
* A LoadBalancer for use with the `Ingress`. For `microk8s` users, refer to [the `microk8s` README for Ingress](../ingress/microk8s/README.md)

# Steps

> [!IMPORTANT]
> All command example assume you are in the root of this cloned repository directory on your local machine.

## Namespace

All deployments will be done in the namespace `example001`

Create the namespace:

```shell
kubectl apply -f persisted_volumes/example001/namespace.yaml 
```

## Content Preparation

In order to prepare the static web page, follow these instructions on the server hosting the NFS share:

```shell
# The same directory previously created as described in nfs-for-microk8s.md
export NFS_DATA_PATH=$PWD/data

# prepare a directory for our site
mkdir -p $NFS_DATA_PATH/websites/examples/static_01

# Clone https://github.com/charliebritton/website-placeholder as an example site
# Any other example will also do - if you have your own pages, that is also 100% fine
cd $NFS_DATA_PATH/websites/examples/static_01
git clone https://github.com/charliebritton/website-placeholder.git
cd website-placeholder
rm -frR README.md LICENSE .git/ .gitignore
```

## PVC Preparation

Make sure you set the `NFS_SERVER_HOST` environment variable to point to your NFS server.

```shell
export NFS_SERVER_HOST=....
```

Deploy the storage class:

```shell
envsubst < persisted_volumes/example001/sc-nfs.yaml | kubectl apply -f -
```

## Main deployment

Finally, deploy the main web application:

```shell
kubectl apply -f persisted_volumes/example001/deployment.yaml 
```

# References

* https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes
* https://github.com/kubernetes-csi/csi-driver-nfs/blob/master/docs/driver-parameters.md

<hr />

[main index](../README.md) | back to: [persisted volumes topic index](./README.md)
