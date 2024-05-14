[main index](../README.md)

# Preparations

> [!IMPORTANT]
> The examples rely on a NFS server that will be used to mount Persisted Volumes. It is highly recommended to familiarize yourself with the NFS setup [as documented here](../persisted_volumes/README.md)
>
> The instructions here will assume a setup that reflects the NFS environment described in these documents.

## Step 1 - Prepare directories

On the NFS server, create the directory `admission-scripts`:

```shell
# The same directory previously created as described in nfs-for-microk8s.md
export NFS_DATA_PATH=$PWD/data

# prepare a directory for our site
mkdir -p $NFS_DATA_PATH/admission-scripts
```

Alternatively, if your NFS server is on another machine and assuming your have SSH access, you can also run the commands from your local machine:

```shell
export NFS_SERVER_HOST=....
export NFS_SERVER_USERNAME=...

# You will have to set the full path below, but do not start with a `/` as this will be added in the commands following this one
export NFS_DATA_PATH=...

ssh $NFS_SERVER_USERNAME@$NFS_SERVER_HOST mkdir -p /$NFS_DATA_PATH/admission-scripts
```

## Step 2 - Copy scripts

Copy the scripts [in the `scripts` directory](./scripts/) to the location you created in step 1.

If the NFS directory is on your local machine, you can directly copy it there as shown below:

```shell
cp -vf admission_webhooks/scripts/* $NFS_DATA_PATH/admission-scripts/
```

If the NFS server is on a remote server, you have to copy it over the network, for example:

```shell
# Add the IP address of your NFS server
export NFS_SERVER_HOST=....
export NFS_SERVER_USERNAME=... 
export NFS_DATA_PATH=...

# copy files
scp admission_webhooks/scripts/*  $NFS_SERVER_USERNAME@$NFS_SERVER_HOST:/$NFS_DATA_PATH/admission-scripts/
```

## Step 3 - Deploy the NFS StorageClass

Run the following command:

```shell
# Add the IP address of your NFS server if not added previously
export NFS_SERVER_HOST=....

# Apply the StorageClass
envsubst < admission_webhooks/common_deployments/deployments.yaml | kubectl apply -f -
```

# Next

Proceed to [the initial test deployment](./initial_test_deployment.md) in order to test the example application deployment without any admission webhooks.

<hr />

[main index](../README.md)

