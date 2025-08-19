#!/usr/bin/env bash

cd /code/app

if [ "$USE_TLS" = "0" ]; then
  echo "WARNING: the application has started without the use of TLS termination"
  uvicorn validation_hook:app --host $HOST --port $PORT --workers $WORKERS
else
  echo "no warnings from launcher..."
  uvicorn validation_hook:app --host $HOST --port $PORT --workers $WORKERS --ssl-keyfile=$SSL_KEY_FILE --ssl-certfile=$SSL_CERTIFICATE_FILE
fi
