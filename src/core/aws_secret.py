"""AWS Secret Manager Configuration"""

import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)


def get_rds_secret() -> dict:
    """
    Fetch RDS credentials from AWS Secrets Manager.
    """

    secret_name = os.getenv("AWS_SECRET_NAME")
    region_name = os.getenv("AWS_REGION")

    logger.info("Fetching RDS secret from Secrets Manager")

    session = boto3.session.Session()

    client = session.client(
        service_name="secretsmanager",
        region_name=region_name,
    )

    response = client.get_secret_value(
        SecretId=secret_name,
    )

    secret = response["SecretString"]

    return json.loads(secret)
