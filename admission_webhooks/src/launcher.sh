#!/usr/bin/env bash

WARNING_MESSAGE="no warnings from launcher..."

if [ "$USE_TLS" = "0" ]; then
  WARNING_MESSAGE="WARNING: the application has started without the use of TLS termination"
  uvicorn validation_hook:app --host $HOST --port $PORT --workers $WORKERS
else
  uvicorn validation_hook:app --host $HOST --port $PORT --workers $WORKERS --ssl-keyfile=$SSL_KEY_FILE --ssl-certfile=$SSL_CERTIFICATE_FILE
fi
