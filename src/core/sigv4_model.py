"""
config/sigv4_model.py
──────────────────────
Custom Strands Model that signs every request with SigV4.
Used when the AI Platform team exposes a private API GW endpoint.
"""

import json
import logging
import boto3
import botocore.auth
import botocore.awsrequest
import botocore.credentials
import requests
from typing import Any, Iterable, Optional, TypedDict
from typing_extensions import Unpack

from strands.models.model import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from src.core.settings import settings

logger = logging.getLogger(__name__)


def _assume_role() -> dict:
    sts = boto3.client("sts")
    assumed = sts.assume_role(
        RoleArn=settings.AI_ROLE_ARN,
        RoleSessionName="kyc-agent-session",
        ExternalId=settings.AI_EXTERNAL_ID,
    )
    return assumed["Credentials"]


class SigV4Model(Model):
    """Custom Strands Model that signs every request with SigV4."""

    class ModelConfig(TypedDict):
        model_id:   str
        invoke_url: str
        region:     str

    def __init__(self, **model_config: Unpack[ModelConfig]) -> None:
        self.config = SigV4Model.ModelConfig(**model_config)
        logger.debug("SigV4Model initialized: %s", self.config)

    def update_config(self, **model_config: Unpack[ModelConfig]) -> None:
        self.config.update(model_config)

    def get_config(self) -> ModelConfig:
        return self.config

    # ── Format the request into what the AI Platform endpoint expects ─────────
    def format_request(
        self,
        messages: Messages,
        tool_specs: Optional[list[ToolSpec]] = None,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        formatted_messages = []

        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        formatted_messages.extend(messages)

        return {
            "model":    self.config["model_id"],
            "messages": formatted_messages,
        }

    # ── Convert the AI Platform response into Strands StreamEvents ────────────
    def format_chunk(self, event: Any) -> StreamEvent:
        event_type = event.get("type")

        if event_type == "message_start":
            return {"messageStart": {"role": "assistant"}}

        elif event_type == "content_block_delta":
            return {
                "contentBlockDelta": {
                    "delta": {"text": event.get("delta", {}).get("text", "")}
                }
            }

        elif event_type == "content_block_stop":
            return {"contentBlockStop": {}}

        elif event_type == "message_stop":
            return {"messageStop": {"stopReason": "end_turn"}}

        elif event_type == "message_delta":
            usage = event.get("usage", {})
            return {
                "metadata": {
                    "usage": {
                        "inputTokens":  usage.get("input_tokens", 0),
                        "outputTokens": usage.get("output_tokens", 0),
                        "totalTokens":  usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                    },
                    "metrics": {"latencyMs": 0}
                }
            }

        return {"contentBlockDelta": {"delta": {"text": ""}}}

    # ── Sign and fire the request, yield StreamEvents back to Strands ─────────
    def stream(self, request: Any) -> Iterable[Any]:
        creds = _assume_role()

        boto_creds = botocore.credentials.Credentials(
            access_key=creds["AccessKeyId"],
            secret_key=creds["SecretAccessKey"],
            token=creds["SessionToken"],
        )

        body = json.dumps(request)
        url  = self.config["invoke_url"]

        aws_request = botocore.awsrequest.AWSRequest(
            method="POST",
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
        )

        signer = botocore.auth.SigV4Auth(boto_creds, "execute-api", self.config["region"])
        signer.add_auth(aws_request)

        prepped  = aws_request.prepare()
        response = requests.post(url, data=body, headers=dict(prepped.headers))
        response.raise_for_status()

        data = response.json()

        # Yield the StreamEvents Strands expects
        yield {"type": "message_start"}

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        yield {"type": "content_block_delta", "delta": {"text": content}}

        yield {"type": "content_block_stop"}
        yield {"type": "message_stop"}