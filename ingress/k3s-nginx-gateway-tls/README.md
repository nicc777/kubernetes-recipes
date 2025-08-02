# K3s with Nginx Gateway Fabric with TLS termination via Lets-Encrypt

This recipe was developed and tested early August 2025.

> [!IMPORTANT]
> The intent of this recipe is to get going quickly in a local development environment. For `lets-encrypt`, a staging certificate is used, which means the TLS certificate will not be trusted by a web browser.
>
> The recipe assumes DNS is maintained in AWS Route 53 - adjust the DNS related configuration (including registrar credentials) to suite your needs.

Basic features covered in this recipe:

* Uninstall a previous deployment
* Install a fresh cluster
* Install the Nginx Gateway Fabric
* Install `cert-manager`
* Configure TLS via `cert-manager` and `lets-encrypt` via AWS Route 53 DNS
* Test Web Server with TLS Gateway and normal unencrypted service (demo application)

![design](./design.png)
