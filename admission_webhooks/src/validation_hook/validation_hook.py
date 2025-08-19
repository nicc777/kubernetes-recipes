import json
import copy
import os
from datetime import datetime
import traceback

from fastapi import FastAPI, HTTPException

app = FastAPI()


RESPONSE_TEMPLATE = {
    "apiVersion": "admission.k8s.io/v1",
    "kind": "AdmissionReview",
    "response": {"uid": "", "allowed": True},
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
        print("{} - [INFO] {}".format(datetime.utcnow(), message))

    def debug(self, message):
        if debug is True:
            print("{} - [DEBUG] {}".format(datetime.utcnow(), message))

    def error(self, message):
        print("{} - [ERROR] {}".format(datetime.utcnow(), message))


logger = Logger()
logger.info("READY")
logger.debug("Debug Enabled")


@app.get("/")
def root():
    return {"message": "ok"}


@app.post("/validate")
def post_validate(data: dict):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            logger.error("EXCEPTION: {}".format(traceback.format_exc()))
    if isinstance(data, dict) is False:
        raise HTTPException(
            status_code=400, detail="Expected a dict but go {}".format(type(data))
        )
    logger.debug("DATA: {}".format(json.dumps(data)))
    uid = None
    validation_result = True
    if "request" in data:
        if "uid" in data["request"]:
            uid = data["request"]["uid"]
    if uid is None:
        raise HTTPException(status_code=400, detail="Could not determine the UID")
    result = copy.deepcopy(RESPONSE_TEMPLATE)
    result["response"]["uid"] = uid
    result["response"]["allowed"] = validation_result
    return result
