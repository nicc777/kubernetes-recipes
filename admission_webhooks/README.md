[main index](../README.md)

# Index

| Topic(s) / Tag(s)                                                                                                                        | Documentation Link                                                              |  Notes                                                                                                                            |
|------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| <ul><li>distro:microk8s</li><li>version:1.28.9</li><li>version:1.30.0</li><li>kubernetes:PersistedVolume</li><li>product:nfs</li></ul>   | [Preparing NFS and scripts for deployment](./nfs_preparations.md)               | For the examples to be useful, some additional preparations need to be made.                                                      |
| <ul><li>example</li><li>deployment</li><li>ValidatingWebhookConfiguration</li></ul>                                                      | [ValidatingWebhookConfiguration](./validating_webhook_deployments/README.md)    | An example of a validating webhook that will ensure every deployment have resource limits set.                                    |
| <ul><li>example</li><li>deployment</li><li>MutatingWebhookConfiguration</li></ul>                                                        | [MutatingWebhookConfiguration](./mutating_webhook_deployments/README.md)        | An example of a mutating webhook that will ensure that the maximum replica count of a deployment does not exceed a certain value. |

> [!NOTE]
> For this content, I drew a lot of inspiration from the wonderful blog posts from Kristijan Mitevski:
>
> * [Writing a Kubernetes Validating Webhook using Python](https://kmitevski.com/writing-a-kubernetes-validating-webhook-using-python/)
> * [Kubernetes Mutating Webhook with Python and FastAPI](https://kmitevski.com/kubernetes-mutating-webhook-with-python-and-fastapi/)
>
> Although these excellent resources exist, I do implement my own versions here to have an example implementation in case the above resource somehow disappear.

<hr />

[main index](../README.md)

<!--
Template for tag list:

<ul>
  <li></li>
</ul>
-->
