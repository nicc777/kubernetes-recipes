# kubernetes-recipes

Some recipes, how-to and step-by-step instruction on various things around Kubernetes and it's eco system.

> [!WARNING]
> The content provided here are for experimentation and learning. It is not intended for production systems and in many cases may ignore security configurations required for production systems.
>
> USE AT YOUR OWN RISK

# Recommendations for Local Testing

Some tests involve running of some Python scripts or apps on your local machine.

It is highly recommended to run the scripts from a virtual environment. To create a virtual environment:

```shell
# Create
python3 -m venv venv

# Activate 
. venv/bin/activate

# Install requirements
pip3 install -r requirements.txt
```

# Content Links

| Topics                | Link                                                              | Notes                                                                                        |
|-----------------------|-------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| Index of all examples | [index of examples](./all_examples.md) |  |
| Ingress               | [Ingress and API Gateway Topics](/ingress/README.md) |  |
| Storage               | [Persisted Volume Topic Index](./persisted_volumes/README.md) | Index page for further content regarding local storage, persisted volumes and related topics |

> [!NOTE]
> All content hosted in this repo are my field notes and I may include many additional links to external sources which I consulted at the time of producing content. If you spot errors, please feel free to open an issue of create a pull request.
