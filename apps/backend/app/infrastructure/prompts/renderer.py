"""Prompt renderer — composes and renders prompt layers into model-ready messages.

Combines templates from the PromptRegistry with dynamic state, context,
and task data to produce the final prompt that is sent to the model.
Supports the five-layer composition from PRD 13.3.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.infrastructure.prompts.registry import PromptRegistry

logger = logging.getLogger(__name__)


class LayerRenderer(Protocol):
    """Protocol for rendering a single prompt layer."""

    def render(self, layer_name: str, context: dict[str, Any]) -> str:
        """Render a prompt layer with the given context."""
        ...


@dataclass
class RenderedPrompt:
    """A fully assembled prompt ready for the model.

    Contains the layer messages that form the conversation input,
    plus metadata about what was included.
    """

    messages: list[dict[str, str]] = field(default_factory=list)
    token_estimate: int = 0
    layers_included: list[str] = field(default_factory=list)
    prompt_manifest_version: str = ""
    context_chunk_ids: list[str] = field(default_factory=list)


class PromptRenderer:
    """Assembles layered prompts from registry templates and dynamic state.

    Composes the five layers from PRD 13.3 in order:
    L1 Identity, L2 Policy, L3 State, L4 Context, L5 Task.

    Usage:
        renderer = PromptRenderer(registry)
        result = renderer.render_response_prompt(state, context, task)
    """

    def __init__(self, registry: PromptRegistry) -> None:
        self._registry = registry

    def render_system_prompt(
        self,
        state_context: dict[str, Any] | None = None,
    ) -> str:
        """Render the system-level prompt (L1 identity + L2 policy).

        Args:
            state_context: Optional dynamic state to inject into policy layers.

        Returns:
            Combined system prompt string.
        """
        parts: list[str] = []

        identity_templates = self._registry.get_identity_layer()
        for tpl in identity_templates:
            parts.append(tpl.content)

        policy_templates = self._registry.get_policy_layer()
        for tpl in policy_templates:
            parts.append(tpl.content)

        return "\n\n".join(parts)

    def render_response_prompt(
        self,
        state_text: str = "",
        context_text: str = "",
        task_text: str = "",
        chunk_ids: list[str] | None = None,
    ) -> RenderedPrompt:
        """Render the full response prompt with all layers.

        Args:
            state_text: L3 structured state (slots, score, progress).
            context_text: L4 retrieved context or deferral instruction.
            task_text: L5 task instruction (next question, objective).
            chunk_ids: Chunk IDs used in context (for provenance).

        Returns:
            A RenderedPrompt with messages ready for the chat API.
        """
        system = self.render_system_prompt()
        layers: list[str] = []

        # L3 State
        if state_text:
            layers.append("state")

        # L4 Context
        if context_text:
            layers.append("context")

        # L5 Task
        if task_text:
            layers.append("task")

        # Build messages array
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
        ]

        user_content_parts: list[str] = []
        if state_text:
            user_content_parts.append(f"<state>\n{state_text}\n</state>")
        if context_text:
            user_content_parts.append(
                f"<context>\n{context_text}\n</context>"
            )
        if task_text:
            user_content_parts.append(f"<task>\n{task_text}\n</task>")

        if user_content_parts:
            messages.append(
                {"role": "user", "content": "\n\n".join(user_content_parts)}
            )

        return RenderedPrompt(
            messages=messages,
            token_estimate=self._estimate_tokens(messages),
            layers_included=layers,
            prompt_manifest_version=self._registry.manifest_version,
            context_chunk_ids=chunk_ids or [],
        )

    def render_structured_prompt(
        self,
        template_id: str,
        context: dict[str, Any] | None = None,
    ) -> RenderedPrompt:
        """Render a structured-output prompt (classification, extraction).

        These use compact task-specific prompts without the full persona.

        Args:
            template_id: The task template ID to render.
            context: Optional context variables for the template.

        Returns:
            A RenderedPrompt with minimal messages.
        """
        template = self._registry.get(template_id)
        messages = [
            {"role": "system", "content": template.content},
        ]
        if context:
            context_str = "\n".join(
                f"{k}: {v}" for k, v in context.items() if v is not None
            )
            messages.append({"role": "user", "content": context_str})

        return RenderedPrompt(
            messages=messages,
            token_estimate=self._estimate_tokens(messages),
            layers_included=[template_id],
            prompt_manifest_version=self._registry.manifest_version,
        )

    @staticmethod
    def _estimate_tokens(messages: list[dict[str, str]]) -> int:
        """Rough token estimate from character count."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return int(total_chars / 4)
