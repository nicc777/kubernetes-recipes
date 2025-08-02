# K3s with Nginx Gateway Fabrix with TLS termination via Lets-Encrypt

This recipe was developed and tested early August 2025.

> [!IMPORTANT]
> The intent of this recipe is to get going quickly in a local development environment. For `lets-encrypt`, a staging certificate is used, which means the TLS certificate will not be trusted by a web browser.
>
> The recipe assumes DNS is maintained in AWS Route 53 - adjust the DNS related configuration (including registrar credentials) to suite your needs.
