import copy
import os
from datetime import datetime, timezone
import traceback
import uuid
import socket
import json
import base64

from fastapi import FastAPI

from kr8s.objects import Namespace

app = FastAPI()


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


QUALIFYING_NAMESPACES = ["test-*", "prod-*"]


QUALIFYING_NAMESPACE_LABELS = {
    "shared-gateway-access": "true",
}


ADD_QUALIFYING_NAMESPACE_LABELS_IF_NOT_EXISTS = False
if os.getenv("ADD_QUALIFYING_NAMESPACE_LABELS_IF_NOT_EXISTS", "1").lower()[0] in (
    "1",
    "t",
    "e",
    "o",
):  # 1, true, enabled, on/ok
    ADD_QUALIFYING_NAMESPACE_LABELS_IF_NOT_EXISTS = True


RESPONSE_TEMPLATE = {
    "apiVersion": "admission.k8s.io/v1",
    "kind": "AdmissionReview",
    "response": {"uid": "", "allowed": True},
}

RESPONSE_TEMPLATE_WITH_PATCHES = {
    "apiVersion": "admission.k8s.io/v1",
    "kind": "AdmissionReview",
    "response": {
        "uid": "",
        "allowed": True,
        "patchType": "JSONPatch",
        "patch": "",
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
    def info(self, message, request_id: str = "no-request-id"):
        print(
            "{} - [{}] - [INFO] {}".format(
                datetime.now(tz=timezone.utc), request_id, message
            )
        )

    def debug(self, message, request_id: str = "no-request-id"):
        if debug is True:
            print(
                "{} - [{}] - [DEBUG] {}".format(
                    datetime.now(tz=timezone.utc), request_id, message
                )
            )

    def error(self, message, request_id: str = "no-request-id"):
        print(
            "{} - [{}] - [ERROR] {}".format(
                datetime.now(tz=timezone.utc), request_id, message
            )
        )

    def warning(self, message, request_id: str = "no-request-id"):
        print(
            "{} - [{}] - [WARNING] {}".format(
                datetime.now(tz=timezone.utc), request_id, message
            )
        )


logger = Logger()
logger.info("READY")
logger.debug("Debug Enabled")


def is_resolvable(fqdn: str, request_id: str = "no-request-id") -> bool:
    try:
        socket.gethostbyname(fqdn)
        return True
    except socket.gaierror:
        logger.error("EXCEPTION: {}".format(traceback.format_exc()), request_id)
    return False


def ignore_namespace(namespace: str, request_id: str = "no-request-id") -> bool:
    for must_ignore_name in NAMESPACE_NAMES_TO_IGNORE:
        ignore_name_final = must_ignore_name.lower()
        if must_ignore_name.endswith("*"):
            ignore_name_final = must_ignore_name.lower().split("*")[0]
            if namespace.lower().startswith(ignore_name_final) is True:
                return True
        else:
            if namespace.lower() == ignore_name_final:
                return True
    return False


def get_namespace_patches(namespace: str, current_labels: dict) -> dict:
    result = dict()
    result["doPatch"] = False
    result["patches"] = list()
    # CHECK AND ADD LABELS IF REQUIRED
    for q_name, q_value in QUALIFYING_NAMESPACE_LABELS.items():
        match_found = False
        if q_name in current_labels:
            if q_value == current_labels[q_name]:
                match_found = True
            else:
                logger.error(
                    'Namespace "{}" found qualifying label  "{}", but expected value "{}" did not match current value "{}"'.format(
                        namespace, q_name, q_value, current_labels[q_name]
                    )
                )
                return result
        if (
            match_found is False
            and ADD_QUALIFYING_NAMESPACE_LABELS_IF_NOT_EXISTS is True
        ):
            result["doPatch"] = True
            result["patches"].append({q_name: q_value})
            logger.info(
                'Qualifying namespace "{}" was missing label "{}: {}" - label will be added as a reqult of the environment value ADD_QUALIFYING_NAMESPACE_LABELS_IF_NOT_EXISTS is set to 1'.format(
                    namespace, q_name, q_value
                )
            )
    return result


def get_qualified_namespace_patches(namespace: str, object_data: dict) -> dict:
    result = dict()
    result["doPatch"] = False
    result["patches"] = list()
    namespace_qualifies = False
    for ns in QUALIFYING_NAMESPACES:
        ns_pattern = ns.lower()
        if ns_pattern.endswith("*"):
            include_name_final = ns_pattern.lower().split("*")[0]
            if namespace.lower().startswith(include_name_final) is True:
                logger.debug(
                    "Service created in namespace `{}` matches qualifying criteria...".format(
                        namespace
                    )
                )
                namespace_qualifies = True
            else:
                if namespace.lower() == include_name_final:
                    logger.debug(
                        "Service created in namespace `{}` matches qualifying criteria...".format(
                            namespace
                        )
                    )
                namespace_qualifies = True
    if namespace_qualifies is True:
        result = get_namespace_patches(
            namespace=namespace, current_labels=object_data["labels"]
        )
    return result


def data_validation(data: dict | None) -> dict:
    object_data = dict()
    object_data["warnings"] = list()
    if data is None:
        return {"error": "data cannot be NoneType"}
    if isinstance(data, dict) is False:
        return {"error": "data must be a dictionary type"}
    if "request" not in data:
        return {"error": "request key not present"}
    if "operation" not in data["request"]:
        return {"error": "request.operation key not present"}

    if data["request"]["operation"] not in ("CREATE", "MODIFY"):
        object_data["warnings"].append("request.operation can be ignored")
        return object_data

    if "object" not in data["request"]:
        return {"error": "request.object key not present"}
    if "uid" not in data["request"]:
        return {"error": "request.uid key not present"}

    if "kind" not in data["request"]["object"]:
        return {"error": "request.object.kind key not present"}
    if "metadata" not in data["request"]["object"]:
        return {"error": "request.object.metadata key not present"}
    if "name" not in data["request"]["object"]["metadata"]:
        return {"error": "request.object.metadata.name key not present"}
    return object_data


def get_request_object_data(data: dict) -> dict:
    object_data = data_validation(data=data)
    if "error" in object_data:
        return object_data

    object_data["kind"] = data["request"]["object"]["kind"].lower()
    object_data["name"] = data["request"]["object"]["metadata"]["name"]
    object_data["namespace"] = data["request"]["object"]["metadata"]["namespace"]
    object_data["annotations"] = dict()
    if "annotations" in data["request"]["object"]["metadata"]:
        if data["request"]["object"]["metadata"]["annotations"] is not None:
            object_data["annotations"] = data["request"]["object"]["metadata"][
                "annotations"
            ]
    object_data["labels"] = dict()
    if "labels" in data["request"]["object"]["metadata"]:
        if data["request"]["object"]["metadata"]["labels"] is not None:
            object_data["labels"] = data["request"]["object"]["metadata"]["labels"]

    return object_data


def build_response(
    uid: str,
    warnings: list | None = None,
    validation_result: bool = False,
    validation_failed_reason: str = "Validation Failed",
    message: str = "Check the validation web hook logs for more information.",
    patch: str | None = None,
    request_id: str = "none",
) -> dict:
    result = copy.deepcopy(RESPONSE_TEMPLATE)
    if validation_result is False:
        result["response"]["uid"] = uid
        result["response"]["allowed"] = validation_result
        result["response"]["status"] = dict()
        result["response"]["status"]["code"] = 403
        result["response"]["status"]["message"] = validation_failed_reason
        return result
    if patch is not None and validation_result is True:
        result = copy.deepcopy(RESPONSE_TEMPLATE_WITH_PATCHES)
        result["response"]["uid"] = uid
        result["response"]["allowed"] = validation_result
        result["response"]["patch"] = patch
    if warnings is not None:
        result["response"]["warnings"] = warnings
    logger.info("Final Response: {}".format(json.dumps(result, indent=4)), request_id)
    return result


def add_warning(current_warnings: list | None, warning_message: str) -> list:
    warnings = list()
    if current_warnings is not None:
        warnings = copy.deepcopy(current_warnings)
    warnings.append(warning_message)
    return warnings


def get_uid(data: dict) -> str:
    try:
        return data["request"]["uid"]
    except:
        logger.error(traceback.format_exc())
        return ""


def add_label_patch(
    object_data: dict = dict(), label_patches: list = list(), request_id: str = "none"
) -> list:
    operations = list()
    if len(object_data["labels"]) == 0 and len(label_patches) > 0:
        operations.append({"op": "add", "path": "/metadata/labels", "value": {}})

    for label_patch_data in label_patches:
        for k, v in label_patch_data.items():
            operations.append(
                {
                    "op": "add",
                    "path": "/metadata/labels/{}".format(k),
                    "value": "{}".format(v),
                },
            )
    return operations


def encode_dict_as_json_base64(data: dict | list, request_id: str = "none") -> str:
    json_string = json.dumps(data)
    base64_encoded_bytes = base64.b64encode(json_string.encode("utf-8"))
    result = base64_encoded_bytes.decode("utf-8")
    logger.debug("Original Data : {}".format(json.dumps(data, indent=4)), request_id)
    logger.debug("Patch Value   : {}".format(result), request_id)
    return result


@app.get("/")
def root():
    return {"message": "ok"}


@app.post("/mutate")
def post_validate(data: dict):
    request_id = str(uuid.uuid4())
    logger.debug("Raw Input data: {}".format(json.dumps(data, indent=4)), request_id)
    object_data = get_request_object_data(data=data)
    logger.debug(
        "Validated data: {}".format(json.dumps(object_data, indent=4)), request_id
    )
    uid = get_uid(data=data)
    warnings = None
    try:
        if "error" in object_data:
            return build_response(
                uid=uid,
                validation_result=False,
                validation_failed_reason="General annotation validation failure. Please check the validation webhook logs.",
                message=object_data["error"],
                request_id=request_id,
            )
        if object_data["kind"] != "namespace":
            if ignore_namespace(namespace=object_data["namespace"]) is False:
                qualified_namespace_patches = get_qualified_namespace_patches(
                    namespace=object_data["namespace"], object_data=object_data
                )
                if qualified_namespace_patches["doPatch"] is True:
                    logger.info(
                        'Namespace "{}" requires patching of labels'.format(
                            object_data["namespace"]
                        )
                    )
                    operations = add_label_patch(
                        object_data=object_data,
                        label_patches=qualified_namespace_patches["patches"],
                        request_id=request_id,
                    )
                    return build_response(
                        uid=uid,
                        validation_result=True,
                        validation_failed_reason="",
                        message=object_data["error"],
                        request_id=request_id,
                        patch=encode_dict_as_json_base64(
                            data=operations, request_id=request_id
                        ),
                    )
                else:
                    logger.info(
                        'No patches for namespace "{}"'.format(object_data["namespace"])
                    )

        return build_response(
            uid=uid,
            validation_result=True,
            validation_failed_reason="",
            message="",
            warnings=warnings,
            request_id=request_id,
        )

    except:
        logger.error(traceback.format_exc())
        return build_response(
            uid=uid,
            validation_result=False,
            validation_failed_reason="Validation process threw an exception",
            message="Please check the web hook logs for the exception stack trace",
            request_id=request_id,
        )
