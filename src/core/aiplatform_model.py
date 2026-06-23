"""Strands custom model provider for the BoI AI Platform gateway.

The built-in Strands `BedrockModel` provider talks directly to Bedrock and only
needs model_id, region and AWS credentials. Tenants do NOT call Bedrock directly:
they call the AI Platform gateway (a Private API Gateway endpoint), which runs
validation, rate limiting, guardrails and the model invocation, then returns a
single JSON response.

So the integration is a custom Strands model provider that:
  1. authenticates with SigV4 against API Gateway (service name "execute-api"),
     using the tenant's own AWS role credentials (no keys to manage), and
  2. uses the AI Platform request/response contract (tenantId + prompt), not the
     Bedrock Converse shape.
"""

import json
import os

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from strands import Agent
from strands.models.model import Model


class AIPlatformModel(Model):
    """Strands model provider for the BoI AI Platform gateway."""

    def __init__(self, endpoint, tenant_id, region="eu-west-1", model_id="eu.amazon.nova-pro-v1:0"):
        self.endpoint = endpoint          # the Private API Gateway invoke URL we shared
        self.tenant_id = tenant_id        # your assigned tenantId
        self.region = region
        self.model_id = model_id
        self._session = boto3.Session()

    # --- Strands config plumbing ---
    def update_config(self, **kwargs):
        self.__dict__.update(kwargs)

    def get_config(self):
        return {
            "endpoint": self.endpoint,
            "tenant_id": self.tenant_id,
            "region": self.region,
            "model_id": self.model_id,
        }

    # --- the actual call ---
    def _invoke(self, prompt):
        # AI Platform gateway request contract. Required: tenantId, prompt
        # (max 10000 chars). Optional: modelId, maxTokens, temperature.
        # The gateway has no system-prompt field; it is not sent.
        payload = json.dumps({
            "tenantId": self.tenant_id,
            "prompt": prompt,
            "modelId": self.model_id,
        })

        creds = self._session.get_credentials().get_frozen_credentials()
        aws_req = AWSRequest(
            method="POST",
            url=self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        SigV4Auth(creds, "execute-api", self.region).add_auth(aws_req)

        resp = requests.post(self.endpoint, data=payload, headers=dict(aws_req.headers), timeout=30)
        resp.raise_for_status()
        # Gateway 200 body: {"text", "model", "usage", "stopReason", "latencyMs"}
        return resp.json()["text"]

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        # take the latest user turn as the prompt
        prompt = ""
        for m in messages:
            if m.get("role") == "user":
                for block in m.get("content", []):
                    if "text" in block:
                        prompt = block["text"]

        text = self._invoke(prompt)

        # our gateway is non-streaming: emit the full response as one block
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": text}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError("Structured output not supported via the gateway yet.")


# --- usage: same shape as your existing Strands code ---
if __name__ == "__main__":
    model = AIPlatformModel(
        endpoint=os.environ["AI_PLATFORM_ENDPOINT"],   # the invoke URL we shared
        tenant_id=os.environ["AI_PLATFORM_TENANT_ID"], # your tenantId
        region="eu-west-1",
    )
    agent = Agent(model=model)
    response = agent("Give 10 countries in Africa that are not commonly known.")
    print(response)
