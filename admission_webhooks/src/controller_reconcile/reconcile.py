import os
import time
from datetime import datetime, timezone
import json
import traceback

import kr8s
from kr8s.objects import new_class


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
        httproute_objects.append(httproute_object.raw)
    logger.debug(
        "Found {} HTTPRoute Objects in namespace {}".format(
            len(httproute_objects, namespace)
        )
    )
    return httproute_objects


def ignore_namespace(namespace: str) -> bool:
    logger.debug("Checking if namespace `{}` should be processed...".format(namespace))
    for must_ignore_name in NAMESPACE_NAMES_TO_IGNORE:
        ignore_name_final = must_ignore_name.lower()
        if must_ignore_name.endswith("*"):
            ignore_name_final = must_ignore_name.lower().split("*")[0]
            if namespace.lower().startswith(ignore_name_final) is True:
                logger.warning(
                    "Service created in namespace `{}` will be ignored...".format(
                        namespace
                    )
                )
                return True
        else:
            if namespace.lower() == ignore_name_final:
                logger.warning(
                    "Service created in namespace `{}` will be ignored...".format(
                        namespace
                    )
                )
                return True
    return False


# def get_httproute_object_linked_to_service(
#     httproute_objects: list, service
# ) -> dict | None:
#     current_httproute_object = None
#
#     return current_httproute_object


def get_current_service_status(service_status: box.Box) -> dict:
    auto_httproute_status = dict()
    auto_httproute_status["reason"] = "not-required"
    auto_httproute_status["created"] = False
    conditions = getattr(service_status, "conditions", list())
    logger.debug("Retrieved {} status items".format(len(conditions)))
    for condition in conditions:
        # {'type': 'AutoHTTPRouteCreated', 'status': 'True', 'lastTransitionTime': '2025-08-27T04:39:39Z', 'reason': 'provisioned', 'message': ''}
        condition_type = getattr(condition, "type", None)
        if condition_type is not None:
            if condition_type == "AutoHTTPRouteCreated":
                condition_created_as_str = getattr(
                    condition, "status", "false"
                ).lower()[0]
                auto_httproute_status["reason"] = getattr(
                    condition, "reason", "pending"
                )
                auto_httproute_status["created"] = False
                if condition_created_as_str.startswith("t"):
                    auto_httproute_status["created"] = True
    return auto_httproute_status


def patch_service_status(
    namespace: str, service_name: str, mark_as_created: bool = True
):
    if mark_as_created is True:
        # Create status for created httproute object
        pass
    else:
        # Create a status reflecting that a httproute object is not required
        pass


def was_httproute_created_for_service(
    namespace: str,
    service_name: str,
    service_status: box.Box,
    httproute_object_name_for_service: str,
) -> bool:
    current_service_status = get_current_service_status(service_status)
    http_route_object_created_for_service = False
    httproute: HTTPRoute
    for httproute in get_httproute_objects(namespace):
        if httproute_object_name_for_service == httproute.name:
            http_route_object_created_for_service = True
    if (
        getattr(current_service_status, "created", False) is False
        and http_route_object_created_for_service is True
    ):
        patch_service_status(namespace, service_name)
    return http_route_object_created_for_service


def services_requires_httproute(
    namespace: str, service_name: str, annotations: box.Box
) -> bool:
    return False


def create_httproute_for_service(
    namespace: str,
    service_name: str,
    httproute_object_name_for_service: str,
    annoitations: box.Box,
    service_spec: box.Box,
):
    patch_service_status(namespace=namespace, service_name=service_name)
    pass


def remove_httproute_for_service(
    namespace: str, service_name: str, httproute_object_name_for_service: str
):
    try:
        httproute = HTTPRoute.get(
            name=httproute_object_name_for_service, namespace=namespace
        )
        httproute.delete()
        patch_service_status(
            namespace=namespace, service_name=service_name, mark_as_created=False
        )
    except:
        logger.error("EXCEPTION: {}".format(traceback.format_exc()))


def inspect_namespaced_service(
    namespace: str,
    service_name: str,
    service_status: box.Box,
    annotations: box.Box,
    service_spec: box.Box,
):
    httproute_object_name_for_service = "{}-route".format(service_name)
    if (
        was_httproute_created_for_service(
            namespace=namespace,
            service_name=service_name,
            service_status=service_status,
            httproute_object_name_for_service=httproute_object_name_for_service,
        )
        is False
    ):
        if services_requires_httproute(namespace, service_name, annotations) is True:
            create_httproute_for_service(
                namespace=namespace,
                service_name=service_name,
                httproute_object_name_for_service=httproute_object_name_for_service,
                annoitations=annotations,
                service_spec=service_spec,
            )
    else:
        if services_requires_httproute(namespace, service_name, annotations) is True:
            remove_httproute_for_service(
                namespace=namespace,
                service_name=service_name,
                httproute_object_name_for_service=httproute_object_name_for_service,
            )


def run():
    while True:
        for service in kr8s.get("services", namespace=kr8s.ALL):
            if ignore_namespace(service.namespace) is False:
                inspect_namespaced_service(
                    namespace=service.namespace,
                    service_name=service.name,
                    service_status=service.status,
                    httproute_objects=get_httproute_objects(service.namespace),
                    annotations=service.annotations,
                    service_spec=service.spec,
                )
        time.sleep(15)


if __name__ == "__main__":
    run()
