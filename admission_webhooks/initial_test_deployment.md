[main index](../README.md)

# Preparations

> [!IMPORTANT]
> These instructions should be followed AFTER [preparation of the Persisted Volumes](./nfs_preparations.md)

# Test Deployment

In order to test your setup and the NFS share, run the following to do an initial test deployment:

```shell
kubectl apply -f admission_webhooks/test_application_deployments/example004_deployment.yaml
```

Test:

```shell
# Set as an environment variable
export INGRESS=`kubectl get service ingress -n ingress -o yaml | yq ".status.loadBalancer.ingress[0].ip"`

# Open the URL in a web browser
xdg-open http://$INGRESS/example004/

# Alternative test from the command line:
curl http://$INGRESS/example004/
```

# Next...

Proceed to either one of the following:

* [ValidatingWebhookConfiguration](./validating_webhook_deployments/README.md) 
* [MutatingWebhookConfiguration](./mutating_webhook_deployments/README.md)

<hr />

[main index](../README.md)

