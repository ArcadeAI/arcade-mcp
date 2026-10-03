"""Invocation-local input requests with signed, replayable continuation state."""

import hashlib
import hmac
import json
import math
import time
from typing import Any, Literal

import jwt
from pydantic import BaseModel, ConfigDict

from arcade_core.schema import ToolCallProtocol


class ElicitationResponse(BaseModel):
    action: Literal["accept", "decline", "cancel"]
    content: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")


class InputRequired(BaseException):
    """Control transfer to the invocation boundary, outside tool error adapters."""

    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        super().__init__("Input required")


class Elicitation:
    """Replay earlier inputs, then yield at the next unanswered input request.

    Retries execute the tool again. Authors must make any side effects before
    elicit idempotent and keep input request ordering deterministic across retries;
    no suspended coroutine or pending-interaction store exists.
    """

    def __init__(self, protocol: ToolCallProtocol, secret: str, binding: dict[str, Any]) -> None:
        self.protocol = protocol
        self.secret = secret
        self.binding = hashlib.sha256(
            json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.responses: dict[str, Any] = {}
        self.index = 0
        if protocol.request_state:
            try:
                state = jwt.decode(
                    protocol.request_state,
                    self._state_key(),
                    algorithms=["HS256"],
                    audience="elicitation",
                    options={"require": ["aud", "exp", "ver", "binding", "responses", "pending"]},
                )
            except jwt.InvalidTokenError as error:
                raise ValueError("Invalid or expired elicitation state") from error
            if state["ver"] != 1 or state["binding"] != self.binding:
                raise ValueError("Invalid elicitation state binding")
            self.responses = state["responses"]
            pending = state["pending"]
            if pending in protocol.input_responses:
                self.responses[pending] = protocol.input_responses[pending]

    def _state_key(self) -> bytes:
        material = self.secret.encode()
        if len(material) < 32:
            raise ValueError("Elicitation requires a worker secret of at least 32 bytes")
        return hmac.digest(material, b"arcade-elicitation-state-v1", "sha256")

    async def elicit(
        self,
        message: str,
        schema: dict[str, Any] | None = None,
        mode: str | None = None,
        url: str | None = None,
        elicitation_id: str | None = None,
        timeout: float = 900.0,
    ) -> ElicitationResponse:
        """Request input using this invocation's current caller declaration.

        Timeout bounds each emitted continuation's lifetime, capped at fifteen
        minutes. Re-emitting an unanswered request starts a fresh lifetime;
        this is not an overall deadline for the tool's multi-round flow.
        """
        effective_mode = "form" if mode is None else mode
        self.index += 1
        key = str(self.index)
        if key in self.responses:
            return ElicitationResponse.model_validate(self.responses[key])

        capability = self.protocol.capabilities.get("elicitation")
        if not isinstance(capability, dict) or (
            effective_mode not in capability and not (effective_mode == "form" and not capability)
        ):
            raise ValueError(f"Client did not declare elicitation {effective_mode} support")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Elicitation timeout must be a finite positive number")

        params: dict[str, Any] = {"message": message}
        if mode is not None:
            params["mode"] = mode
        if effective_mode == "form":
            if url is not None or elicitation_id is not None:
                raise ValueError("URL parameters are not supported in form mode")
            params["requestedSchema"] = (
                schema if schema is not None else {"type": "object", "properties": {}}
            )
        elif effective_mode == "url":
            if schema is not None or not url or not elicitation_id:
                raise ValueError("URL mode requires url and elicitation_id, without schema")
            params.update(url=url, elicitationId=elicitation_id)
        else:
            raise ValueError(f"Unsupported elicitation mode: {effective_mode}")
        token = jwt.encode(
            {
                "aud": "elicitation",
                "ver": 1,
                "exp": time.time() + min(timeout, 900),
                "binding": self.binding,
                "responses": self.responses,
                "pending": key,
            },
            self._state_key(),
            algorithm="HS256",
        )
        raise InputRequired({
            "content": [],
            "resultType": "input_required",
            "requestState": token,
            "inputRequests": {key: {"method": "elicitation/create", "params": params}},
        })
