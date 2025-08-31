import os
import time
from datetime import datetime, timezone
import json
import traceback
import copy
import hashlib

import kr8s
from kr8s.objects import new_class, object_from_spec
from kr8s.objects import Service, APIObject


NAMESPACE_NAMES_TO_IGNORE = [
    "argocd",
    "bootstrapping",
    "cert-manager",
    "default",
    "devops",
    "kube-*",
    "nfs",
    "nginx-gateway",
    "tekton-*",
]


HTTPROUTE_TEMPLATES = {
    "redirect": {
        "apiVersion": "gateway.networking.k8s.io/v1",
        "kind": "HTTPRoute",
        "metadata": {
            "name": "__NAME__",
            "namespace": "__NAMESPACE__",
            "annotations": dict(),
        },
        "spec": {
            "parentRefs": [
                {
                    "name": "__GATEWAY_NAME__",
                    "sectionName": "__GATEWAY_SECTION_NAME__",
                }
            ],
            "hostnames": ["__FQDN__"],
            "rules": [
                {
                    "filters": [
                        {
                            "type": "RequestRedirect",
                            "requestRedirect": {
                                "scheme": "__GATEWAY_TARGET_SECTION_NAME__",
                                "statusCode": 301,
                            },
                        }
                    ]
                }
            ],
        },
    },
    "default": {
        "apiVersion": "gateway.networking.k8s.io/v1",
        "kind": "HTTPRoute",
        "metadata": {
            "name": "__NAME__",
            "namespace": "__NAMESPACE__",
            "annotations": dict(),
        },
        "spec": {
            "parentRefs": [
                {"name": "__GATEWAY_NAME__", "sectionName": "__GATEWAY_SECTION_NAME__"}
            ],
            "hostnames": ["__FQDN__"],
            "rules": [
                {
                    "backendRefs": [
                        {"name": "__SERVICE_NAME__", "port": "__SERVICE_TARGET_PORT__"}
                    ]
                }
            ],
        },
    },
}


debug = False
if os.getenv("DEBUG", "0").lower()[0] in (
    "1",
    "t",
    "e",
    "o",
):  # 1, true, enabled, on/ok
    debug = True


class Logger:
    def info(self, message):
        print("{} - [INFO] {}".format(datetime.now(tz=timezone.utc), message))

    def debug(self, message):
        if debug is True:
            print("{} - [DEBUG] {}".format(datetime.now(tz=timezone.utc), message))

    def error(self, message):
        print("{} - [ERROR] {}".format(datetime.now(tz=timezone.utc), message))

    def warning(self, message):
        print("{} - [WARNING] {}".format(datetime.now(tz=timezone.utc), message))


logger = Logger()
logger.info("READY")
logger.debug("Debug Enabled")


HTTPRoute = new_class(
    kind="HTTPRoute",
    version="gateway.networking.k8s.io/v1",
    namespaced=True,
    scalable=False,
)


def get_httproute_objects(namespace) -> list:
    httproute_objects = list()
    for httproute_object in kr8s.get("httproutes", namespace=namespace):
        httproute_objects.append(httproute_object)
    logger.debug(
        "Found {} HTTPRoute Objects in namespace {}".format(
            len(httproute_objects), namespace
        )
    )
    return httproute_objects


class HttpRouteObjects:
    def __init__(self, namespace: str) -> None:
        self.httproute_objects = dict()
        self.namespace = namespace
        self.httproute_service_links = dict()
        self.refresh_objects()

    def refresh_objects(self):
        self.httproute_service_links = dict()
        httproute_object: APIObject
        for httproute_object in get_httproute_objects(namespace=self.namespace):
            annotations = httproute_object.annotations
            if annotations is not None:
                linked_service_name = getattr(
                    annotations, "auto-httproute.linked-service-name", None
                )
                if linked_service_name is not None:
                    self.httproute_objects[httproute_object.name] = httproute_object
                    if httproute_object.name not in self.httproute_service_links:
                        self.httproute_service_links[httproute_object.name] = (
                            linked_service_name
                        )
                    logger.info(
                        'Found HTTPRoute named "{}" to service named "{}" in namespace "{}"'.format(
                            httproute_object.name, linked_service_name, self.namespace
                        )
                    )

    def exists(self, name: str) -> bool:
        o: APIObject
        for n, o in self.httproute_objects.items():
            if o.namespace == self.namespace and o.name == name:
                return True
        return False

    def delete(self, name: str):
        o: APIObject
        for n, o in self.httproute_objects.items():
            if o.namespace == self.namespace and o.name == name:
                o.delete()
                logger.info(
                    'Deleted HTTPRoute named "{}" in namespace "{}"'.format(
                        o.name, self.namespace
                    )
                )
        self.refresh_objects()

    def create(self, manifest: dict) -> bool:
        logger.debug(
            "Attempting to apply config: {}".format(json.dumps(manifest, indent=4))
        )
        try:
            if manifest["metadata"]["namespace"] is not None:
                if manifest["metadata"]["namespace"] != self.namespace:
                    logger.error(
                        'Cannot create HTTPRoute object as the namespace "{}" does not match the current working namespace "{}"'.format(
                            manifest["metadata"]["namespace"], self.namespace
                        )
                    )
                    return False
            new_object = object_from_spec(manifest, allow_unknown_type=True)
            new_object.create()
            logger.info(
                'Created HTTPRoute named "{}" in namespace "{}"'.format(
                    new_object.name, self.namespace
                )
            )
        except:
            logger.error("EXCEPTION: {}".format(traceback.format_exc()))
            return False
        self.refresh_objects()
        return True

    def names(self) -> tuple:
        names = tuple(self.httproute_objects.keys())
        logger.info(
            "Found {} managed HTTPRoute objects in namespace {}".format(
                len(names), self.namespace
            )
        )
        return names


def ignore_namespace(namespace: str) -> bool:
    logger.debug("Checking if namespace `{}` should be processed...".format(namespace))
    for must_ignore_name in NAMESPACE_NAMES_TO_IGNORE:
        ignore_name_final = must_ignore_name.lower()
        if must_ignore_name.endswith("*"):
            ignore_name_final = must_ignore_name.lower().split("*")[0]
            if namespace.lower().startswith(ignore_name_final) is True:
                logger.debug(
                    "Service created in namespace `{}` will be ignored...".format(
                        namespace
                    )
                )
                return True
        else:
            if namespace.lower() == ignore_name_final:
                logger.debug(
                    "Service created in namespace `{}` will be ignored...".format(
                        namespace
                    )
                )
                return True
    return False


def get_timestamp_as_str() -> str:
    now_utc = datetime.now(tz=timezone.utc)
    return now_utc.isoformat().replace("+00:00", "Z")


def get_namespaces(include_ignored_namespaces: bool = False) -> list:
    namespaces = list()
    for namespace in kr8s.get(kind="namespaces", namespace=kr8s.ALL):
        if include_ignored_namespaces is True:
            namespaces.append(namespace.name)
        elif ignore_namespace(namespace=namespace.name) is False:
            namespaces.append(namespace.name)
    logger.info(
        "Found {} namespaces (including ignored: {})".format(
            len(namespaces), include_ignored_namespaces
        )
    )
    return namespaces


def calculate_name_based_on_keys(
    input_keys: tuple, max_len: int = 60, prefix: str = "auto-httproute"
) -> str:
    raw_name = "/".join(input_keys)
    name = "{}-{}".format(prefix, hashlib.sha256(raw_name.encode("utf-8")).hexdigest())
    if len(name) > max_len:
        name = name[0: max_len - 1]
    return name


def build_httproute_manifest(
    annotation_value_elements: list | tuple,
    namespace: str,
    service: Service,
    original_value: str,
    action: str,
) -> dict:
    manifest = HTTPROUTE_TEMPLATES["default"]
    if action.lower() == "redirect":
        manifest = HTTPROUTE_TEMPLATES["redirect"]
    gateway_name = annotation_value_elements[0]
    gateway_section_name = annotation_value_elements[1]
    fqdn = annotation_value_elements[2]
    target = annotation_value_elements[3]

    httproute_name = calculate_name_based_on_keys(
        input_keys=(
            service.namespace,
            service.name,
            gateway_name,
            gateway_section_name,
            action,
            target,
        )
    )
    manifest["metadata"]["annotations"]["auto-httproute.linked-service-name"] = (
        service.name
    )
    manifest["metadata"]["annotations"]["auto-httproute.action"] = action
    manifest["metadata"]["annotations"]["auto-httproute.config-value"] = original_value
    manifest_json = json.dumps(manifest)

    manifest_json = manifest_json.replace("__NAME__", httproute_name)
    manifest_json = manifest_json.replace("__NAMESPACE__", namespace)
    manifest_json = manifest_json.replace("__GATEWAY_NAME__", gateway_name)
    manifest_json = manifest_json.replace(
        "__GATEWAY_SECTION_NAME__", gateway_section_name
    )
    manifest_json = manifest_json.replace("__FQDN__", fqdn)

    if action.lower() != "redirect":
        target = int(target)
        manifest_json = manifest_json.replace("__SERVICE_NAME__", service.name)
        manifest_json = manifest_json.replace("__SERVICE_TARGET_PORT__", str(target))
    else:
        manifest_json = manifest_json.replace("__GATEWAY_TARGET_SECTION_NAME__", target)

    manifest = json.loads(manifest_json)
    if action.lower() != "redirect":
        logger.debug("manifest={}".format(json.dumps(manifest)))
        manifest["spec"]["rules"][0]["backendRefs"][0]["port"] = int(
            manifest["spec"]["rules"][0]["backendRefs"][0]["port"]
        )
    return manifest


def get_required_httproutes_for_service(service: Service) -> dict:
    """
    auto-httproute.<<custom-ref>>.target-port: <<gateway-name>>/<<section-name>>/<<fqdn>>/<<target-srevice-port>>
    auto-httproute.<<custom-ref>>.redirect: <<gateway-name>>/<<section-name>>/<<fqdn>>/<<target-section-name>>
    """
    httproutes_required = dict()
    namespace = "default"
    if service.namespace is not None:
        namespace = service.namespace

    for k, v in service.annotations.items():
        if k.startswith("auto-httproute.") is True:
            annotation_key_elements = k.split(".")
            if len(annotation_key_elements) > 2:
                action = annotation_key_elements[2]
                annotation_value_elements = v.split("/")
                if len(annotation_value_elements) > 3:
                    manifest = build_httproute_manifest(
                        annotation_value_elements=annotation_value_elements,
                        namespace=namespace,
                        service=service,
                        original_value=v,
                        action=action,
                    )

                    httproutes_required[manifest["metadata"]["name"]] = manifest

    return httproutes_required


def process(httproutes: HttpRouteObjects, service: Service) -> HttpRouteObjects:
    # Key=httproute_name   Val=Manifest dictionary
    httproutes_required = get_required_httproutes_for_service(service=service)
    required_names = tuple(httproutes_required.keys())
    current_names = httproutes.names()
    for current_httproute_name in current_names:
        if current_httproute_name not in required_names:
            httproutes.delete(name=current_httproute_name)
    current_names = httproutes.names()
    for required_name in required_names:
        if required_name not in current_names:
            httproutes.create(httproutes_required[required_name])
    logger.info(
        'Service "{}" in namespace "{}" checked'.format(service.name, service.namespace)
    )
    return httproutes


def run():
    while True:
        for namespace in get_namespaces():
            if ignore_namespace(namespace=namespace) is False:
                httproutes = HttpRouteObjects(namespace=namespace)
                discovered_service_names = list()
                for service in kr8s.get("services", namespace=namespace):
                    discovered_service_names.append(service.name)
                    httproutes = process(httproutes=httproutes, service=service)
                for (
                    httproute_name,
                    service_name,
                ) in httproutes.httproute_service_links.items():
                    if service_name not in discovered_service_names:
                        httproutes.delete(name=httproute_name)
        time.sleep(15)


if __name__ == "__main__":
    run()
