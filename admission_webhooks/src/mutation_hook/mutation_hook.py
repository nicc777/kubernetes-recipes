import copy
import os
from datetime import datetime, timezone
import traceback
import uuid
import socket
import json
import base64

from fastapi import FastAPI

app = FastAPI()


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
    logger.debug(
        "Checking if namespace `{}` should be processed...".format(namespace),
        request_id,
    )
    for must_ignore_name in NAMESPACE_NAMES_TO_IGNORE:
        ignore_name_final = must_ignore_name.lower()
        if must_ignore_name.endswith("*"):
            ignore_name_final = must_ignore_name.lower().split("*")[0]
            if namespace.lower().startswith(ignore_name_final) is True:
                logger.debug(
                    "Service created in namespace `{}` will be ignored...".format(
                        namespace
                    ),
                    request_id,
                )
                return True
        else:
            if namespace.lower() == ignore_name_final:
                logger.debug(
                    "Service created in namespace `{}` will be ignored...".format(
                        namespace
                    ),
                    request_id,
                )
                return True
    return False


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
    if "namespace" not in data["request"]["object"]["metadata"]:
        return {"error": "request.object.metadata.namespace key not present"}

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

    return object_data


def build_response(
    uid: str,
    warnings: list | None = None,
    validation_result: bool = False,
    validation_failed_reason: str = "Validation Failed",
    message: str = "Check the validation web hook logs for more information.",
    patch: str | None = None,
) -> dict:
    result = copy.deepcopy(RESPONSE_TEMPLATE)
    if patch is not None and validation_result is True:
        result = copy.deepcopy(RESPONSE_TEMPLATE_WITH_PATCHES)
        result["response"]["patch"] = encode_dict_as_json_base64(data=add_label_patch())
    result["response"]["uid"] = uid
    result["response"]["allowed"] = validation_result
    if validation_result is False:
        result["response"]["status"] = dict()
        result["response"]["status"]["code"] = 403
        result["response"]["status"]["message"] = validation_failed_reason

    if warnings is not None:
        result["response"]["warnings"] = warnings
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


def add_label_patch() -> dict:
    return {"op": "add", "path": "/metadata/labels/auto-httproute", "value": "true"}


def encode_dict_as_json_base64(data: dict) -> str:
    json_string = json.dumps(data)
    base64_encoded_bytes = base64.b64encode(json_string.encode("utf-8"))
    return base64_encoded_bytes.decode("utf-8")


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
            )
        if len(object_data["warnings"]) > 0:
            warnings = object_data["warnings"]
        if object_data["kind"] != "httproute":
            warnings = add_warning(
                current_warnings=warnings,
                warning_message="Kind {} ignored".format(
                    data["request"]["object"]["kind"]
                ),
            )
            return build_response(
                uid=uid,
                validation_result=True,
                validation_failed_reason="",
                message="",
                warnings=warnings,
            )

        if ignore_namespace(object_data["namespace"], request_id=request_id) is True:
            return build_response(
                uid=uid,
                validation_result=True,
                validation_failed_reason="",
                message="",
                warnings=warnings,
            )

        return build_response(
            uid=uid,
            validation_result=True,
            validation_failed_reason="",
            message="",
            warnings=warnings,
            patch=encode_dict_as_json_base64(data=add_label_patch()),
        )

    except:
        logger.error(traceback.format_exc())
        return build_response(
            uid=uid,
            validation_result=False,
            validation_failed_reason="Validation process threw an exception",
            message="Please check the web hook logs for the exception stack trace",
        )
