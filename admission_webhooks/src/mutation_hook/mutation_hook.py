import json
import copy
import os
from datetime import datetime, timezone
import traceback
import base64
import socket
import uuid

from fastapi import FastAPI, HTTPException

from kr8s.objects import new_class

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

ANNOTATION_KEYS = (
    "devops-expose-public",
    "devops-public-record-name",
    "devops-service-target-port",
    "devops-skip-http-route-to-https-actions",
    "devops-skip-mutation",
    "devops-gateway-name: private-gateway",
    "devops-gateway-http-section-name",
    "devops-gateway-https-section-name",
    "devops-domain-name",
)

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


class Annotations:
    def __init__(
        self,
        expose_public: bool = False,
        public_record_name: str | None = None,
        service_target_port: int | None = None,
        skip_http_route_to_https_actions: bool = False,
        skip_mutation: bool = False,
        gateway_name: str | None = None,
        gateway_http_section_name: str = "http",
        gateway_https_section_name: str = "https",
        domain_name: str | None = None,
        is_managed_by_argocd: bool = False,
        original_devops_annotations: dict = dict(),
        request_id: str = "no-request-id",
    ) -> None:
        self.expose_public = expose_public
        self.public_record_name = public_record_name
        self.service_target_port = service_target_port
        self.skip_http_route_to_https_actions = skip_http_route_to_https_actions
        self.skip_mutation = skip_mutation
        self.gateway_name = gateway_name
        self.gateway_http_section_name = gateway_http_section_name
        self.gateway_https_section_name = gateway_https_section_name
        self.domain_name = domain_name
        self.request_id = request_id
        self.validation_passed = True
        self.fail_reason = list()
        self.warnings = list()
        self.is_managed_by_argocd = is_managed_by_argocd
        self.original_devops_annotations = original_devops_annotations
        self.patch_replacements = dict()
        self.patch_additions = dict()
        self.patch_deletions = dict()
        self.validate_annotations()

    def to_dict_as_is(self) -> dict:
        d = dict()
        d["annotations"] = dict()
        d["warnings"] = self.warnings
        d["validation-pass"] = self.validation_passed
        d["failure-reasons"] = self.fail_reason
        d["is-managed-by-argocd"] = self.is_managed_by_argocd
        d["original-devops-annotations"] = self.original_devops_annotations
        d["patch-replacements"] = dict()
        d["patch-additions"] = dict()
        d["patch-deletions"] = dict()
        d["patches"] = list()
        d["encoded_patches"] = None
        d["annotations"]["devops-expose-public"] = self.expose_public
        d["annotations"]["devops-public-record-name"] = self.public_record_name
        d["annotations"]["devops-service-target-port"] = self.service_target_port
        d["annotations"]["devops-skip-http-route-to-https-actions"] = (
            self.skip_http_route_to_https_actions
        )
        d["annotations"]["devops-skip-mutation"] = self.skip_mutation
        d["annotations"]["devops-gateway-name"] = self.gateway_name
        d["annotations"]["devops-gateway-http-section-name"] = (
            self.gateway_http_section_name
        )
        d["annotations"]["devops-gateway-https-section-name"] = (
            self.gateway_https_section_name
        )
        d["annotations"]["devops-domain-name"] = self.domain_name
        return d

    def validate_annotations(self):
        if self.gateway_name is None and self.expose_public is True:
            self.validation_passed = False
            self.fail_reason.append(
                "Annotation devops-gateway-name is required when devops-expose-public is set to true."
            )
        if self.gateway_http_section_name is None and self.expose_public is True:
            self.validation_passed = False
            self.fail_reason.append(
                "Annotation devops-gateway-http-section-name is required when devops-expose-public is set to true."
            )
        if self.gateway_https_section_name is None and self.expose_public is True:
            self.validation_passed = False
            self.fail_reason.append(
                "Annotation devops-gateway-https-section-name is required when devops-expose-public is set to true."
            )
        if self.domain_name is None and self.expose_public is True:
            self.validation_passed = False
            self.fail_reason.append(
                "Annotation devops-domain-name is required when devops-expose-public is set to true."
            )
        if self.validation_passed is True and self.expose_public is True:
            fqdn = "{}.{}".format(self.public_record_name, self.domain_name)
            if is_resolvable(fqdn=fqdn, request_id=self.request_id) is False:
                self.warnings.append(
                    "The current FQDN does not resolve! You may need to still update your DNS. FQDN={}".format(
                        fqdn
                    )
                )
        if self.is_managed_by_argocd is True:
            self.warnings.append(
                "Service is managed by ArgoCD and therefore annotations will not by updated - This should have no effect on your application."
            )

    def _determine_patches(self, d: dict) -> dict:
        if d["is-managed-by-argocd"] is False:
            for annotation_key in ANNOTATION_KEYS:
                original_value = None
                if annotation_key in self.original_devops_annotations:
                    original_value = self.original_devops_annotations[annotation_key]

                sanitized_value = None
                if annotation_key in d["annotations"]:
                    sanitized_value = d["annotations"][annotation_key]

                valus_as_str = "{}".format(sanitized_value)
                if isinstance(sanitized_value, bool):
                    valus_as_str = valus_as_str.lower()

                if original_value is None and sanitized_value is not None:
                    # ADDITION
                    d["patch-additions"][annotation_key] = dict()
                    d["patch-additions"][annotation_key]["op"] = "add"
                    d["patch-additions"][annotation_key]["path"] = (
                        "/metadata/annotations/{}".format(annotation_key)
                    )
                    d["patch-additions"][annotation_key]["value"] = valus_as_str
                    d["patches"].append(d["patch-additions"][annotation_key])
                elif original_value is not None and sanitized_value is None:
                    # REMOVAL
                    d["patch-additions"][annotation_key] = dict()
                    d["patch-additions"][annotation_key]["op"] = "remove"
                    d["patch-additions"][annotation_key]["path"] = (
                        "/metadata/annotations/{}".format(annotation_key)
                    )
                    d["patch-additions"][annotation_key]["value"] = original_value
                    d["patches"].append(d["patch-additions"][annotation_key])
                else:
                    if original_value != sanitized_value:
                        # MODIFIED
                        d["patch-additions"][annotation_key] = dict()
                        d["patch-additions"][annotation_key]["op"] = "replace"
                        d["patch-additions"][annotation_key]["path"] = (
                            "/metadata/annotations/{}".format(annotation_key)
                        )
                        d["patch-additions"][annotation_key]["value"] = valus_as_str
                        d["patches"].append(d["patch-additions"][annotation_key])

                if len(d["patches"]) > 0:
                    json_string = json.dumps(d["patches"])
                    base64_encoded_bytes = base64.b64encode(json_string.encode("utf-8"))
                    d["encoded_patches"] = base64_encoded_bytes.decode("utf-8")

        else:
            d["patch-replacements"] = dict()
            d["patch-additions"] = dict()
            d["patch-deletions"] = dict()
            d["patches"] = list()
        return d

    def to_dict_sanitized(self) -> dict:
        d = self.to_dict_as_is()
        if self.expose_public is False:
            if "devops-public-record-name" in d["annotations"]:
                del d["annotations"]["devops-public-record-name"]
            if "devops-gateway-name" in d["annotations"]:
                del d["annotations"]["devops-gateway-name"]
            if "devops-gateway-http-section-name" in d["annotations"]:
                del d["annotations"]["devops-gateway-http-section-name"]
            if "devops-gateway-https-section-name" in d["annotations"]:
                del d["annotations"]["devops-gateway-https-section-name"]
            if "devops-domain-name" in d["annotations"]:
                del d["annotations"]["devops-domain-name"]
        d = self._determine_patches(d)
        return d


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
                logger.warning(
                    "Service created in namespace `{}` will be ignored...".format(
                        namespace
                    ),
                    request_id,
                )
                return True
        else:
            if namespace.lower() == ignore_name_final:
                logger.warning(
                    "Service created in namespace `{}` will be ignored...".format(
                        namespace
                    ),
                    request_id,
                )
                return True
    return False


def validate_request_data(data: dict, request_id: str = "no-request-id") -> dict:
    e = Exception("Event Parsing Error. Aborting.")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            logger.error("EXCEPTION: {}".format(traceback.format_exc()), request_id)
    if isinstance(data, dict) is False:
        raise Exception("Expected a dict but go {}".format(type(data)))
    if "kind" not in data:
        logger.error(
            "Expected key `kind` was not found. data: {}".format(json.dumps(data)),
            request_id,
        )
        raise e
    if "request" not in data:
        logger.error(
            "Expected key `request` was not found. data: {}".format(json.dumps(data)),
            request_id,
        )
        raise e
    if "uid" not in data["request"]:
        logger.error(
            "Expected key `request.uid` was not found. data: {}".format(
                json.dumps(data)
            ),
            request_id,
        )
        raise e
    if "object" not in data["request"]:
        logger.error(
            "Expected key `request.object` was not found. data: {}".format(
                json.dumps(data)
            ),
            request_id,
        )
        raise e
    if "metadata" not in data["request"]["object"]:
        logger.error(
            "Expected key `request.object.metadata` was not found. data: {}".format(
                json.dumps(data)
            ),
            request_id,
        )
        raise e
    return data


def get_service_ports(data: dict, request_id: str = "no-request-id") -> list:
    ports = list()
    logger.debug(
        "Parsing ports from Service spec: {}".format(
            json.dumps(data["request"]["object"]["spec"]["ports"])
        ),
        request_id,
    )
    for ports_def in data["request"]["object"]["spec"]["ports"]:
        ports.append(int(ports_def["port"]))
    logger.info("Service ports: {}".format(ports), request_id)
    if len(ports) == 0:
        raise Exception(
            "At least one port must be deinfed when defining a Service object"
        )
    return ports


def parse_data_to_generate_annotation_object(
    data: dict, request_id: str = "no-request-id"
) -> Annotations:
    service_ports = get_service_ports(data=data)
    metadata = data["request"]["object"]["metadata"]
    expose_public = False
    public_record_name = None
    service_target_port = None
    skip_http_route_to_https_actions = False
    skip_mutation = False
    gateway_name = os.getenv("DEFAULT_GATEWAY_NAME", "private-gateway")
    gateway_http_section_name = os.getenv("DEFAULT_HTTP_SECTION_NAME", "http")
    gateway_https_section_name = os.getenv("DEFAULT_HTTPS_SECTION_NAME", "https")
    domain_name = None
    is_managed_by_argocd = False
    original_devops_annotations = dict()
    if "annotations" in metadata:
        for md_key, md_val in metadata["annotations"].items():
            logger.debug(
                "Evaluating Annotation: {}: {}".format(md_key, md_val), request_id
            )
            if md_key.lower().startswith("devops-"):
                original_devops_annotations[md_key] = md_val
            if md_key == "devops-expose-public":
                if md_val.lower().startswith("t"):
                    expose_public = True
            elif md_key == "devops-public-record-name":
                public_record_name = "{}".format(md_val)
            elif md_key == "devops-service-target-port":
                service_target_port = int(md_val)
            elif md_key == "devops-skip-http-route-to-https-actions":
                if md_val.lower().startswith("t"):
                    skip_http_route_to_https_actions = True
            elif md_key == "devops-skip-mutation":
                if md_val.lower().startswith("t"):
                    skip_mutation = True
            elif md_key == "devops-gateway-name":
                gateway_name = "{}".format(md_val)
            elif md_key == "devops-gateway-http-section-name":
                gateway_http_section_name = "{}".format(md_val)
            elif md_key == "devops-gateway-https-section-name":
                gateway_https_section_name = "{}".format(md_val)
            elif md_key == "devops-domain-name":
                domain_name = "{}".format(md_val)
            elif "argocd" in md_key.lower():
                is_managed_by_argocd = True
            else:
                logger.info("Skipped annotation named `{}`".format(md_key), request_id)
    if service_target_port is None:
        service_target_port = int(service_ports[0])
    return Annotations(
        expose_public=expose_public,
        public_record_name=public_record_name,
        service_target_port=service_target_port,
        skip_http_route_to_https_actions=skip_http_route_to_https_actions,
        skip_mutation=skip_mutation,
        gateway_name=gateway_name,
        gateway_http_section_name=gateway_http_section_name,
        gateway_https_section_name=gateway_https_section_name,
        domain_name=domain_name,
        is_managed_by_argocd=is_managed_by_argocd,
        original_devops_annotations=original_devops_annotations,
        request_id=request_id,
    )


HTTPRoute = new_class(
    kind="HTTPRoute",
    version="gateway.networking.k8s.io/v1",
    namespaced=True,
    scalable=False,
)


def _service_build_annotation_object(data: dict, request_id: str) -> tuple:
    validation_result = True
    validation_failed_reason = None
    warnings = None
    annotations: Annotations | None = None
    try:
        if (
            ignore_namespace(
                namespace=data["request"]["namespace"], request_id=request_id
            )
            is True
        ):
            logger.info(
                "Service in namespace `{}` will be ignored".format(
                    data["request"]["namespace"]
                ),
                request_id,
            )
        else:
            logger.info(
                "Evaluating service for namespace `{}`".format(
                    data["request"]["namespace"]
                ),
                request_id,
            )
            logger.debug("DATA: {}".format(json.dumps(data)))
            if "kind" in data:
                if data["kind"] == "AdmissionReview":
                    annotations = parse_data_to_generate_annotation_object(
                        data=data, request_id=request_id
                    )
                    logger.info(
                        "Effective Annotations: {}".format(
                            json.dumps(annotations.to_dict_sanitized())
                        ),
                        request_id,
                    )
                    validation_result = annotations.validation_passed
                    if len(annotations.fail_reason) > 0:
                        validation_failed_reason = " ".join(annotations.fail_reason)
                    if len(annotations.warnings) > 0:
                        warnings = copy.deepcopy(annotations.warnings)
                else:
                    logger.warning(
                        "Received an unkown data object kind. Expecting a `AdmissionReview` but got `{}`".format(
                            data["kind"]
                        ),
                        request_id,
                    )
            else:
                logger.warning("Unknown data object", request_id)
    except:
        logger.error("EXCEPTION: {}".format(traceback.format_exc()), request_id)

    return (annotations, validation_result, validation_failed_reason, warnings)


def _service_build_result_for_failed_validation(
    uid: str | None,
    validation_failed_reason: str | None,
    warnings: list | None,
    request_id: str,
) -> dict:
    result = copy.deepcopy(RESPONSE_TEMPLATE)
    result["response"]["status"] = dict()
    if validation_failed_reason is not None:
        result["response"]["status"]["code"] = 403
        result["response"]["status"]["message"] = validation_failed_reason
    else:
        result["response"]["status"]["code"] = 403
        result["response"]["status"]["message"] = (
            "Check the validation webhook logs for details."
        )
    if warnings is not None:
        result["response"]["warnings"] = warnings
    logger.debug(
        "Final Return Data: {}".format(json.dumps(result, indent=4)), request_id
    )
    result["response"]["uid"] = uid
    result["response"]["allowed"] = False
    return result


def _service_build_final_response(
    annotations: Annotations | None,
    uid: str | None,
    warnings: list | None,
    request_id: str,
) -> dict:
    result = copy.deepcopy(RESPONSE_TEMPLATE)
    if annotations is not None:
        annotation_data = annotations.to_dict_sanitized()
        if (
            len(annotation_data["patches"]) > 0
            and annotation_data["encoded_patches"] is not None
        ):
            result = copy.deepcopy(RESPONSE_TEMPLATE_WITH_PATCHES)
            result["response"]["patch"] = annotation_data["encoded_patches"]

    result["response"]["uid"] = uid
    result["response"]["allowed"] = True
    if warnings is not None:
        result["response"]["warnings"] = warnings
    logger.debug(
        "Final Return Data: {}".format(json.dumps(result, indent=4)), request_id
    )
    return result


@app.get("/")
def root():
    return {"message": "ok"}


@app.post("/mutate")
def post_validate(data: dict):
    request_id = str(uuid.uuid4())
    uid = None
    try:
        data = validate_request_data(data=data)
        uid = data["request"]["uid"]
    except:
        logger.error(traceback.format_exc())
        validation_result = False
        validation_failed_reason = "General annotation validation failure. Please check the validation webhook logs."
    annotations: Annotations | None
    validation_result: bool
    validation_failed_reason: str | None
    warnings: list
    annotations, validation_result, validation_failed_reason, warnings = (
        _service_build_annotation_object(data, request_id)
    )

    if validation_result is False:
        return _service_build_result_for_failed_validation(
            uid, validation_failed_reason, warnings, request_id
        )

    return _service_build_final_response(annotations, uid, warnings, request_id)
