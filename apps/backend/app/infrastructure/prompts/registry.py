"""Prompt registry — loads, versions, validates, and retrieves prompt templates.

Manages the lifecycle of all prompt templates. Templates are stored as
versioned Markdown/Jinja2 files on disk and referenced through a manifest.
The registry provides a single interface for prompt loading and retrieval.

References: PRD 13.3, AI Blueprint Section 10, NFR-26
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

import yaml

logger = logging.getLogger(__name__)


class PromptCategory(str, Enum):
    """Categories of prompt templates.

    Matches the layer structure from PRD 13.3:
    L1 Identity, L2 Policy, L3 State, L4 Context, L5 Task
    """

    IDENTITY = "identity"
    POLICY = "policy"
    STATE = "state"
    CONTEXT = "context"
    TASK = "task"


@dataclass
class PromptMetadata:
    """Metadata for a single prompt template.

    Carries version identifier, file path, category, and description.
    """

    template_id: str
    path: str
    version: str = "1.0.0"
    category: str = PromptCategory.TASK.value
    description: str = ""
    content_hash: str = ""

    @property
    def full_path(self) -> str:
        """Return the resource path under the prompts directory."""
        return f"app/resources/prompts/{self.path}"


@dataclass
class PromptVersion:
    """Version information for a prompt template."""

    template_id: str
    version: str
    previous_version: str | None = None
    changelog: str = ""
    content_hash: str = ""
    valid_from: str = ""


@dataclass
class ManifestData:
    """Represents the prompt manifest file structure."""

    version: str = ""
    templates: dict[str, dict] = field(default_factory=dict)


class PromptLoader(Protocol):
    """Protocol for loading prompt template content."""

    def load(self, path: str) -> str:
        """Load prompt content from the given path."""
        ...

    def exists(self, path: str) -> bool:
        """Check if a prompt template exists at the given path."""
        ...


class FilePromptLoader:
    """Loads prompt templates from the filesystem."""

    def __init__(self, base_path: str | None = None) -> None:
        self.base_path = Path(base_path or "app/resources/prompts")

    def load(self, path: str) -> str:
        """Read prompt template content from a file."""
        full_path = self.base_path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {full_path}")
        return full_path.read_text(encoding="utf-8")

    def exists(self, path: str) -> bool:
        """Check if a prompt template file exists."""
        return (self.base_path / path).exists()


@dataclass
class PromptTemplate:
    """A loaded and validated prompt template."""

    template_id: str
    content: str
    metadata: PromptMetadata
    version: PromptVersion | None = None


class PromptRegistry:
    """Central registry for all prompt templates.

    Loads the manifest at construction, validates all referenced templates
    exist, and provides lookup by template ID. Templates are cached in
    memory after first load.

    Usage:
        registry = PromptRegistry()
        template = registry.get("identity")
        content = template.content
    """

    def __init__(
        self,
        manifest_path: str = "app/resources/prompts/manifest.yaml",
        base_path: str = "app/resources/prompts",
        loader: PromptLoader | None = None,
    ) -> None:
        self._manifest_path = Path(manifest_path)
        self._base_path = base_path
        self._loader = loader or FilePromptLoader(base_path)
        self._templates: dict[str, PromptTemplate] = {}
        self._manifest: ManifestData = ManifestData()
        self._loaded: bool = False

    @property
    def manifest_version(self) -> str:
        """Version of the loaded manifest."""
        return self._manifest.version

    def load_all(self) -> dict[str, PromptTemplate]:
        """Load all templates from the manifest.

        Returns:
            Dict of template_id to PromptTemplate.

        Raises:
            FileNotFoundError: If the manifest or any template file is missing.
            ValueError: If the manifest is malformed.
        """
        self._load_manifest()
        templates: dict[str, PromptTemplate] = {}

        for template_id, entry in self._manifest.templates.items():
            path = entry.get("path", "")
            version = entry.get("version", "1.0.0")

            if not self._loader.exists(path):
                raise FileNotFoundError(
                    f"Template '{template_id}' not found at '{path}' "
                    f"(referenced in manifest)"
                )

            content = self._loader.load(path)
            category = self._infer_category(template_id)

            metadata = PromptMetadata(
                template_id=template_id,
                path=path,
                version=version,
                category=category,
            )

            template = PromptTemplate(
                template_id=template_id,
                content=content,
                metadata=metadata,
            )
            templates[template_id] = template

        self._templates = templates
        self._loaded = True
        logger.info(
            "Loaded %d prompt templates (manifest v%s)",
            len(templates),
            self._manifest.version,
        )
        return templates

    def get(self, template_id: str) -> PromptTemplate:
        """Get a single template by ID.

        Loads all templates on first access if not yet loaded.

        Args:
            template_id: The template identifier from the manifest.

        Returns:
            The requested PromptTemplate.

        Raises:
            KeyError: If the template_id is not in the manifest.
        """
        if not self._loaded:
            self.load_all()
        if template_id not in self._templates:
            raise KeyError(
                f"Unknown prompt template: '{template_id}'. "
                f"Available: {list(self._templates.keys())}"
            )
        return self._templates[template_id]

    def get_by_category(self, category: str) -> list[PromptTemplate]:
        """Get all templates in a given category.

        Args:
            category: The PromptCategory value to filter by.

        Returns:
            List of PromptTemplate instances in the category.
        """
        if not self._loaded:
            self.load_all()
        return [
            t for t in self._templates.values()
            if t.metadata.category == category
        ]

    def get_identity_layer(self) -> list[PromptTemplate]:
        """Get L1 Identity templates."""
        return self.get_by_category(PromptCategory.IDENTITY)

    def get_policy_layer(self) -> list[PromptTemplate]:
        """Get L2 Policy templates."""
        return self.get_by_category(PromptCategory.POLICY)

    def get_task_templates(self) -> list[PromptTemplate]:
        """Get L5 Task templates."""
        return self.get_by_category(PromptCategory.TASK)

    def validate_all(self) -> list[str]:
        """Validate all templates exist and have required metadata.

        Returns:
            List of validation error messages (empty if all valid).
        """
        errors: list[str] = []
        try:
            self.load_all()
        except (FileNotFoundError, ValueError) as e:
            errors.append(str(e))
            return errors

        for template_id, template in self._templates.items():
            if not template.content.strip():
                errors.append(f"Template '{template_id}' is empty")
            if not template.metadata.version:
                errors.append(f"Template '{template_id}' has no version")

        return errors

    def reload(self) -> dict[str, PromptTemplate]:
        """Force reload all templates from disk."""
        self._loaded = False
        self._templates.clear()
        return self.load_all()

    def _load_manifest(self) -> None:
        """Load and parse the manifest YAML file."""
        if not self._manifest_path.exists():
            raise FileNotFoundError(
                f"Prompt manifest not found: {self._manifest_path}"
            )

        raw = self._manifest_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)

        if not isinstance(data, dict):
            raise ValueError("Prompt manifest is not a valid YAML mapping")

        self._manifest = ManifestData(
            version=str(data.get("version", "")),
            templates=data.get("templates", {}),
        )

        if not self._manifest.templates:
            raise ValueError(
                "Prompt manifest contains no template entries"
            )

    @staticmethod
    def _infer_category(template_id: str) -> str:
        """Infer the prompt category from the template ID prefix."""
        category_map = {
            "identity": PromptCategory.IDENTITY,
            "policy": PromptCategory.POLICY,
            "task": PromptCategory.TASK,
        }
        for prefix, category in category_map.items():
            if template_id.startswith(prefix):
                return category.value
        return PromptCategory.TASK.value
