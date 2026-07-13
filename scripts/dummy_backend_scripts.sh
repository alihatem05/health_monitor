#!/bin/bash
SERVICE_NAME=service-a HEALTH_STATUS=healthy uvicorn dummy.main:app --port 5001 &
SERVICE_NAME=service-b HEALTH_STATUS=unhealthy uvicorn dummy.main:app --port 5002 &
SERVICE_NAME=service-c HEALTH_STATUS=slow uvicorn dummy.main:app --port 5003 &
SERVICE_NAME=service-d HEALTH_STATUS=flaky uvicorn dummy.main:app --port 5004 &
wait