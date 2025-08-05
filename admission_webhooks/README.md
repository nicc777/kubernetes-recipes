[main](../README.md)

<hr />

# Dynamic Admission Control

The [Kubernetes Documentation](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/) provides a good introduction to the topic.

This recipe consists of the following features:

* Preparing a K3s cluster
* Walk through of the Python webhook implementation
* Preparing the certificates for the webhook application
* Deployment of the webhook
* Looking at various test scenarios:
  * Testing the validating webhook
  * Testing the mutating webhook
  * Blocking deployments that fail validation
  * Auto-correcting deployments that would otherwise fail validation
* Complete example: Take a "normal" deployment with a service, and inject a secure proxy sidecar to secure communications to a `Pod`.

<hr />

[main](../README.md)
