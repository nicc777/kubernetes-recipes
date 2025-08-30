import os
import time
from datetime import datetime, timezone
import json
import traceback
import copy

import kr8s
from kr8s.objects import new_class
from kr8s.objects import Service, APIObject
from box import Box


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
        "metadata": {"name": "__NAME__", "namespace": "__NAMESPACE__"},
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
        "metadata": {"name": "__NAME__", "namespace": "__NAMESPACE__"},
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
        httproute_objects.append(httproute_object.raw)
    logger.debug(
        "Found {} HTTPRoute Objects in namespace {}".format(
            len(httproute_objects), namespace
        )
    )
    return httproute_objects


class HttpRouteObjects:
    def __init__(self, namespace: str) -> None:
        self.httproute_objects = list()
        self.namespace = namespace
        self.refresh_objects()

    def refresh_objects(self):
        self.httproute_objects = get_httproute_objects(namespace=self.namespace)

    def exists(self, name: str) -> bool:
        o: APIObject
        for o in self.httproute_objects:
            if o.namespace == self.namespace and o.name == name:
                return True
        return False

    def delete(self, namespace: str, name: str):
        o: APIObject
        for o in self.httproute_objects:
            if o.namespace == namespace and o.name == name:
                o.delete()
        self.refresh_objects()

    def create(self, http_route: APIObject) -> bool:
        if http_route.namespace is not None:
            if http_route.namespace != self.namespace:
                logger.error(
                    'Cannot create HTTPRoute object as the namespace "{}" does not match the current working namespace "{}"'.format(
                        http_route.namespace, self.namespace
                    )
                )
                return False
        http_route.create()
        self.refresh_objects()
        return self.exists(name=http_route.name)

    def new(self, kind: str = "default", parameters: dict = dict()) -> APIObject | None:
        if len(parameters) == 0:
            return None
        data: dict | None
        data = getattr(HTTPROUTE_TEMPLATES, kind, None)
        if data is None:
            return
        data_json = json.dumps(data)
        for k, v in parameters.items():
            data_json = data_json.replace(k, v)
        http_route: APIObject | None
        http_route = None
        try:
            http_route = HTTPRoute(json.loads(data_json))
        except:
            logger.error("EXCEPTION: {}".format(traceback.format_exc()))
        return http_route


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


def get_timestamp_as_str() -> str:
    now_utc = datetime.now(tz=timezone.utc)
    return now_utc.isoformat().replace("+00:00", "Z")


def patch_service_last_probe_time(
    namespace: str, service_name: str, condition: dict | Box | None
):
    if condition is None:
        return
    last_transition_time = getattr(condition, "lastTransitionTime", "unknown")
    if last_transition_time == "unknown":
        return
    try:
        service = Service.get(name=service_name, namespace=namespace)
        patch_payload = {
            "status": {
                "conditions": [
                    {
                        "type": "AutoHTTPRouteReady",
                        "status": getattr(condition, "status", "True"),
                        "reason": getattr(condition, "reason", "default-status"),
                        "messagie": getattr(
                            condition, "message", "Status was set to True"
                        ),
                        "lastTransitionTime": last_transition_time,
                        "lastProbeTime": get_timestamp_as_str(),
                    }
                ]
            }
        }
        service.patch(patch_payload)
    except:
        logger.error("EXCEPTION: {}".format(traceback.format_exc()))


def get_current_service_status(service_status: Box) -> dict:
    auto_httproute_status = dict()
    auto_httproute_status["reason"] = "not-required"
    auto_httproute_status["created"] = False
    conditions = getattr(service_status, "conditions", list())
    logger.debug("Retrieved {} status items".format(len(conditions)))
    for condition in conditions:
        # {'type': 'AutoHTTPRouteReady', 'status': 'True', 'lastTransitionTime': '2025-08-27T04:39:39Z', 'reason': 'provisioned', 'message': ''}
        condition_type = getattr(condition, "type", None)
        if condition_type is not None:
            if condition_type == "AutoHTTPRouteReady":
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
    now_as_str = get_timestamp_as_str()
    condition = {
        "type": "AutoHTTPRouteReady",
        "status": "True",
        "reason": "HTTPRoute-Created",
        "messagie": "A new HTTPRoute Object was created",
        "lastTransitionTime": now_as_str,
        "lastProbeTime": now_as_str,
    }
    if mark_as_created is False:
        condition["status"] = "False"
        condition["reason"] = "HTTPRoute-Not-Created"
        condition["message"] = (
            "A new HTTPRoute object was not created. Existing HTTPRoute objects was removed."
        )
    try:
        service = Service.get(name=service_name, namespace=namespace)
        patch_payload = {
            "status": {
                "conditions": [
                    condition,
                ]
            }
        }
        service.patch(patch_payload)
    except:
        logger.error("EXCEPTION: {}".format(traceback.format_exc()))


def was_httproute_created_for_service(
    namespace: str,
    httproute_object_name_for_service: str,
) -> bool:
    httproute: APIObject
    for httproute in get_httproute_objects(namespace):
        if httproute_object_name_for_service == httproute.name:
            return True
    return False


def services_requires_httproute(annotations: Box) -> bool:
    return False


def remove_httproute_for_service(
    namespace: str, service_name: str, httproute_name: str
):
    try:
        httproute = HTTPRoute.get(name=httproute_name, namespace=namespace)
        httproute.delete()
        patch_service_status(
            namespace=namespace, service_name=service_name, mark_as_created=False
        )
    except:
        logger.error("EXCEPTION: {}".format(traceback.format_exc()))


def create_http_route_from_annotations(
    http_route_objects: HttpRouteObjects,
    httproute_name: str,
) -> bool:
    return False


def inspect_namespaced_service(
    service: Service,
):
    namespace = "default"
    if service.namespace is not None:
        namespace = service.namespace
    httproute_name = "{}-route".format(service.name)
    httproute_objects = HttpRouteObjects(namespace=namespace)
    httproute_required = services_requires_httproute(annotations=service.annotations)
    httproute_exists = httproute_objects.exists(name=httproute_name)
    if httproute_exists is False:
        if httproute_required is True:
            result = create_http_route_from_annotations(
                http_route_objects=HttpRouteObjects(namespace=namespace),
                httproute_name=httproute_name,
            )
            if result is True:
                logger.info(
                    'Created HTTPRoute service named "{}" in namespace "{}"'.format(
                        httproute_name, namespace
                    )
                )
            else:
                logger.error(
                    'Attempt to create HTTPRoute object named "{}" for service "{}" in namespace "{}" FAILED.'.format(
                        httproute_name, service.name, namespace
                    )
                )
    else:
        if httproute_required is False:
            remove_httproute_for_service(
                namespace=namespace,
                service_name=service.name,
                httproute_name=httproute_name,
            )


def run():
    while True:
        for service in kr8s.get("services", namespace=kr8s.ALL):
            if ignore_namespace(service.namespace) is False:
                inspect_namespaced_service(service=service)
        time.sleep(15)


if __name__ == "__main__":
    run()
