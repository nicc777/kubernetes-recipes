[main](../README.md)

<hr />

# Dynamic Admission Control

This recipe shows an example of an admission webhook implementation in Python. The aim is to dynamically create `HTTPRoute` objects when `Service` objects indicate that they should be exposed publicly. This is useful for local development with a cluster containing the [Gateway API](https://gateway-api.sigs.k8s.io/) implementation for ingress. In this scenario, the ingress is handled dynamically and the development deployment only needs to concern itself with creating `Service` objects and add the required annotations to handle the dynamic management of `HTTPRoute` objects.

<!-- toc -->

- [Prerequisites](#prerequisites)
- [Walk Through of the Python Webhook Implementation](#walk-through-of-the-python-webhook-implementation)
  * [Validation](#validation)
  * [Mutation](#mutation)
- [The HTTPRoute Controller](#the-httproute-controller)
  * [Basic Processing Logic](#basic-processing-logic)
- [Preparing the Certificates for the Webhook Applications](#preparing-the-certificates-for-the-webhook-applications)
- [Deployment of the Web Hooks](#deployment-of-the-web-hooks)
- [Looking at various test scenarios](#looking-at-various-test-scenarios)
  * [Testing the validating webhook](#testing-the-validating-webhook)
  * [Testing the mutating webhook](#testing-the-mutating-webhook)
  * [Blocking deployments that fail validation](#blocking-deployments-that-fail-validation)
  * [Auto-correcting deployments that would otherwise fail validation](#auto-correcting-deployments-that-would-otherwise-fail-validation)
- [Complete Example](#complete-example)
- [References](#references)

<!-- tocstop -->

## Prerequisites

These recipes were testing on a `K3s` cluster provisioned according to recipe for running [`k3s` on a Local Development Environment](/bootstrapping/k3s_local_dev/README.md)

The `k3s` Kubernetes distribution already meets all the minimum requirements as set out in the [Kubernetes documentation](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#prerequisites)

> [!NOTE]
> When you want to use your own images, you will also need access to a trusted and private OCI compliant container registry. [The `Zot` project](https://github.com/project-zot/zot) offers a good solution. By default, the images in the GitHub project registry will be used.

> [!IMPORTANT]
> Generally speaking, mutating web hooks should not have side effects (create, update or delete resources), as this needs to be tracked and managed (CRUD actions) as the watched resources are created, updated and deleted. In this example, the mutating web hook will create, update and delete `HTTPRoute` objects. For this specific use case, I find thios acceptable. As a result, the mutating web hook will also require a cache and for this reason an instance of `Valkey` will be used.

## Walk Through of the Python Webhook Implementation

Keeping with the theme of the local development cluster as described in the prerequisite recipe, this recipe will focus on the following admission web hooks:

- A validating web hook that will ensure that pods targeted for development namespaces meet the minimum requirements
- A mutating web hook that will ensure that pods targeted for development namespaces have proper resource limits set

The annotation on a `Service` object required to allow public access:

```yaml
metadata:
  annotations:
    auto-httproute/expose-public: true # Default=false. If HTTPRoute objects link to this service, the deployment/update of this service will be denied. Also, new HTTPRoute objects will be denied.
    auto-httproute/public-record-name: test # [REQUIRED, if service is publicly exposed] 
    auto-httproute/service-target-port: 80 # [REQUIRED, is services have multiple port definitions] Indicate which is the HTTP port. Service HTTPS end-points are not yet supported.
    auto-httproute/skip-http-route-to-https-actions: false # Default=false. If true, the HTTPRoute object allowing HTTP traffic to the service will be allowed, otherwise a redirect to HTTP will be enforced
    auto-httproute/skip-mutation: false # Default=false. If set to true, the mutating web hook will not create HTTPRoute objects. Set this to true if you are providing your own HTTPRoute manifests.
    auto-httproute/gateway-name: private-gateway # Default=private-gateway
    auto-httproute/gateway-http-section-name: http # Default=http
    auto-httproute/gateway-https-section-name: https # Default=https
    auto-httproute/domain-name: null # [REQUIRED, if service is publicly exposed] add the domain name, for example "example.com". The final hostname will therefore be "test.example.com" (based on the public record name annotation.)
```

By default, the following namespaces are excluded from the validation checks:

- `argocd`
- `bootstrapping`
- `cert-manager`
- `default`
- `devops`
- `kube-*`
- `nfs`
- `nginx-gateway`
- `tekton-*`

All other namespaces are considered to be development namespaces. The list is configurable.

### Validation

For any deployment in other namespaces, any deployment that includes `HTTPRoute` configuration will only be allowed if the object has an annotation that specifically allows public access. The validation will also ensure that the DNS domain is included in the white listed domains.

For example, `Deployment`, `StatefulSet` and `Pod` objects may all have a `Service` object to expose the Pod. If the `Service` does NOT have an appropriate annotation, then any `HTTPRoute` that point's to that `Service` will be denied.

The validating web hook will register for the following resources with the relevant validation checks:

- `Service` - Check if the annotations are present. Update the local `Valkey` cache accordingly.
  - Deny conditions:
    - The `auto-httproute/public-record-name` record name was already defined previously
- `HTTPRoute` - Check if the linked service is allowed to expose the HTTP service publicly
  - Deny conditions:
    - The annotations to the linked `Service` was not present
    - The annotation `auto-httproute/expose-public` is not present, or is set to `false`
    - If a corresponding `HTTPRoute` already exist (one will be automatically created by the mutating web hook, unless otherwise indicated by annotation)
    - If multiple ports are defined in the `Service`, but the annotations does not include a `auto-httproute/service-target-port` annotation.
  - Warnings:
    - If the DNS record has not been defined yet, serve a warning.
    - If the annotations indicate the use of a known HTTP port (non-secure) that is NOT automatically redirected to HTTPS
  - Acceptance processing:
    - Register the record as active.

### Mutation

When the `Service` is created/updated, and the annotations indicate that the `Service` is public, this hook will dynamically create `HTTPRoute` objects, depending on the other annotations. Also, when the service is updated, this web hook may create or delete `HTTPRoute` objects.

The default template for the `HTTPRoute` objects is shown below. By default, HTTP traffic will be routed to HTTPS:

```yaml
---
# DEFAULT HTTP Route:
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: __NAME__
spec:
  parentRefs:
  - name: __GATEWAY_NAME__
    sectionName: __GATEWAY_HTTP_SECTION_NAME__
  hostnames:
  - __RECORD_NAME__.__DOMAIN__
  rules:
  - filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: __GATEWAY_HTTPS_SECTION_NAME__
        statusCode: 301
---
# ALTERNATE HTTP Route (service integration allowed):
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: __NAME__
spec:
  parentRefs:
  - name: __GATEWAY_NAME__
    sectionName: __GATEWAY_HTTP_SECTION_NAME__
  hostnames:
  - __RECORD_NAME__.__DOMAIN__
  rules:
  - backendRefs:
    - name: __SERVICE_NAME__
      port: __SERVICE_TARGET_PORT__
---
# DEFAULT HTTPS Route:
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: __NAME__
  labels:
    gateway: __GATEWAY_NAME__
spec:
  parentRefs:
  - name: __GATEWAY_NAME__
    sectionName: __GATEWAY_HTTPS_SECTION_NAME__
  hostnames:
  - __RECORD_NAME__.__DOMAIN__
  rules:
  - backendRefs:
    - name: __SERVICE_NAME__
      port: __SERVICE_TARGET_PORT__
```

The placeholder to annotation mapping is listed next:

| Placeholder | Annotation Mapping |
|---|---|
| `__NAME__` | The name will be the value of the `Service` name with the schema and `-route` appended. For example, a service named `my-service`, will have `HTTPRoute` names of `my-service-http-route` and `my-service-https-route` respectively. |
| `__GATEWAY_NAME__` | `auto-httproute/gateway-name` |
| `__GATEWAY_HTTP_SECTION_NAME__` | `auto-httproute/gateway-http-section-name` |
| `__GATEWAY_HTTPS_SECTION_NAME__` | `auto-httproute/gateway-https-section-name` |
| `__RECORD_NAME__` | `auto-httproute/public-record-name` |
| `__DOMAIN__` | `auto-httproute/domain-name` |

The `Service` will also have updated annotations to reflect the actual values (for those annotations not added).

## The HTTPRoute Controller

### Basic Processing Logic

| Process | Description |
|---|---|
| Watch for Changes | The controller constantly watches the Kubernetes API server for changes to the resources it's responsible for. This is done through a "watch" API call. When an event occurs (a resource is created, updated, or deleted), the controller is notified. |
| Add to Work Queue | When a change is detected, the controller doesn't process it immediately. Instead, it adds the object's unique identifier (e.g., its name and namespace) to a **work queue**. This queue ensures that requests are processed in an orderly and efficient manner. |
| Dequeue and Reconcile | A worker from a pool of goroutines (or threads) picks an item from the work queue. The controller's `Reconcile` function is then invoked with the object's identifier. This function is the heart of the reconciliation loop.|
| Fetch the Desired State | Inside the `Reconcile` function, the controller fetches the latest version of the resource from the API server. This object represents the **desired state** that you, the user, have defined in your manifest. |
| Compare States | The controller then inspects the **current state** of the cluster related to that resource. For a `Deployment`, it would check the number and status of associated `ReplicaSet`s and `Pod`s. It compares the current state against the desired state. |
| Take Action | If a difference is found, the controller takes the necessary action to bridge the gap. |
| Update Status | After taking action, the controller updates the `status` field of the resource to reflect the new current state. This allows you to monitor the controller's progress using commands like `kubectl get` or `kubectl describe`. |
| Repeat | The entire process is a continuous loop. Even if no changes are detected, the controller periodically "re-queues" every object it manages to perform a full reconciliation. This ensures the cluster heals itself from any unlogged or missed state changes, guaranteeing that the current state always converges toward the desired state. |

## Preparing the Certificates for the Webhook Applications

TODO

## Deployment of the Web Hooks

TODO

<!-- NOTE: Deploy via Tekton and ArgoCD. Tekton to clone this repo and create an appropriate ArgoCD Application -->

## Looking at various test scenarios

TODO

### Testing the validating webhook

TODO

### Testing the mutating webhook

TODO

### Blocking deployments that fail validation

TODO

### Auto-correcting deployments that would otherwise fail validation

TODO

## Complete Example

TODO

## References

- [Kubernetes Documentation for Admission Control](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/) (using the standard web hooks)
- [Kubernetes Documentation for Dynamic Admission Control](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/) (Basically what this recipe is about - creating custom admission web hooks)
- [Manage Kubernetes Admission Webhook certificates with cert-manager CA Injector and Vault PKI](https://medium.com/trendyol-tech/manage-kubernetes-admission-webhooks-certificates-with-cert-manager-ca-injector-and-vault-pki-281b065e1044) (Medium, last visited 2025-08-18)

<hr />

[main](../README.md)
