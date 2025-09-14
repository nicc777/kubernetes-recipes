#!/usr/bin/env bash

cd /code/app

if [ "$USE_TLS" = "0" ]; then
  echo "WARNING: the application has started without the use of TLS termination"
  echo
  echo "STARTER CMD: uvicorn ${APP_FILE}:app --host ${HOST} --port ${PORT} --workers ${WORKERS} --log-level debug --no-use-colors"
  uvicorn ${APP_FILE}:app --host $HOST --port $PORT --workers $WORKERS --log-level debug --no-use-colors
else
  echo "no warnings from launcher..."
  echo
  echo "STARTER CMD: uvicorn ${APP_FILE}:app --host ${HOST} --port ${PORT} --workers ${WORKERS} --ssl-keyfile=${SSL_KEY_FILE} --ssl-certfile=${SSL_CERTIFICATE_FILE} --log-level debug --no-use-colors"
  uvicorn ${APP_FILE}:app --host $HOST --port $PORT --workers $WORKERS --ssl-keyfile=$SSL_KEY_FILE --ssl-certfile=$SSL_CERTIFICATE_FILE --log-level debug --no-use-colors
fi
