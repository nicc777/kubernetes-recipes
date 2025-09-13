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
  * [Various Templates based on Annotations](#various-templates-based-on-annotations)
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

## Walk Through of the Python Webhook Implementation

Keeping with the theme of the local development cluster as described in the prerequisite recipe, this recipe will focus on the following admission web hooks:

- A validating web hook that will ensure that pods targeted for development namespaces meet the minimum requirements
- A mutating web hook that will ensure that pods targeted for development namespaces have proper resource limits set

The annotation on a `Service` object required to allow public access:

```yaml
metadata:
  annotations:
    # Choose EITHER "target-port" or "redirect" - NEVER BOTH. Both supplied
    # will lead to potential routing errors that can be hard to resolve.
    #
    # If neither of these annotations are present, any existing HTTPRoute with
    # a calculated target name will be deleted.
    auto-httproute.<<custom-ref>>.target-port: <<gateway-name>>/<<gateway-namespace>>/<<section-name>>/<<fqdn>>/<<target-srevice-port>>
    auto-httproute.<<custom-ref>>.redirect: <<gateway-name>>/<<gateway-namespace>>/<<section-name>>/<<fqdn>>/<<target-section-name>>
```

### Validation

Validation is applied to the `HTTPRoute` object that is deployed to ensure that it is allowed in the given namespace.

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

For other namespaces, a naming convention will be applied to determine which namespaces qualify. In this example, namespaces starting with `test-` or `prod-` will be allowed to provision `HTTPRoute` objects as determined by the relevant annotations.

All other namespaces are considered to be development namespaces and will have no `HTTPRoute` objects created.

In these examples, the lists are not configurable, but can be made configurable by reading a file which can be modified by a `ConfigMap`.

### Mutation

When the `Service` is created/updated, and the annotations indicate that the `Service` is public, this hook will also update annotations to reflect the actual values (as needed).

## The HTTPRoute Controller

### Basic Processing Logic

The [controller source file `reconcile.py`](./src/controller_reconcile/reconcile.py) is a single file application that contains all logic.

![Reconciliation Logic](./admission-Reconciliation-Logic.png)

### Various Templates based on Annotations

The default template for the `HTTPRoute` objects is shown below. By default, HTTP traffic will be routed to HTTPS:

```yaml
---
# DEFAULT HTTP Route:
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: __NAME__
  namespace: __NAMESPACE__
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
  namespace: __NAMESPACE__
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
  namespace: __NAMESPACE__
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
| `__NAMESPACE__` | The target namespace |
| `__GATEWAY_NAME__` | `auto-httproute/gateway-name` |
| `__GATEWAY_HTTP_SECTION_NAME__` | `auto-httproute/gateway-http-section-name` |
| `__GATEWAY_HTTPS_SECTION_NAME__` | `auto-httproute/gateway-https-section-name` |
| `__RECORD_NAME__` | `auto-httproute/public-record-name` |
| `__DOMAIN__` | `auto-httproute/domain-name` |

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
