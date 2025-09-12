"""
System prompt service for managing system prompt files and operations.
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemPromptInfo:
    """Information about a system prompt file."""
    filename: str
    content: str
    preview: str
    word_count: int
    file_path: Path


class SystemPromptService:
    """Service for managing system prompt files and operations."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the system prompt service.

        Args:
            base_dir: Base directory to look for system_prompts folder.
                     If None, uses current working directory.
        """
        self.base_dir = base_dir or Path.cwd()
        self.prompts_dir = self.base_dir / "system_prompts"

    def get_system_prompts_dir(self) -> Path:
        """Get the system prompts directory path."""
        return self.prompts_dir

    def has_system_prompts(self) -> bool:
        """Check if any system prompts are available."""
        if not self.prompts_dir.exists():
            return False

        # Check for any supported file types
        supported_extensions = {'.txt', '.md'}
        for file_path in self.prompts_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                return True

        return False

    def list_system_prompts(self) -> List[SystemPromptInfo]:
        """
        Discover and load all system prompts from system_prompts/ folder.

        Returns:
            List of SystemPromptInfo objects for available system prompts
        """
        if not self.prompts_dir.exists():
            logger.info(f"System prompts directory does not exist: {self.prompts_dir}")
            return []

        prompts = []
        supported_extensions = {'.txt', '.md'}

        try:
            for file_path in self.prompts_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    try:
                        prompt_info = self._load_system_prompt_info(file_path)
                        if prompt_info:
                            prompts.append(prompt_info)
                    except Exception as e:
                        logger.warning(f"Failed to load system prompt {file_path.name}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to list system prompts directory: {e}")
            return []

        # Sort by filename for consistent ordering
        prompts.sort(key=lambda p: p.filename.lower())
        return prompts

    def load_system_prompt_content(self, filename: str) -> Optional[str]:
        """
        Load full content of specific system prompt file.

        Args:
            filename: Name of the system prompt file

        Returns:
            Full content of the system prompt file, or None if not found/error
        """
        file_path = self.prompts_dir / filename

        if not file_path.exists() or not file_path.is_file():
            logger.warning(f"System prompt file not found: {filename}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return content
        except Exception as e:
            logger.error(f"Failed to load system prompt {filename}: {e}")
            return None

    def delete_system_prompt(self, filename: str) -> bool:
        """
        Delete a system prompt file.

        Args:
            filename: Name of the system prompt file to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        file_path = self.prompts_dir / filename

        if not file_path.exists() or not file_path.is_file():
            logger.warning(f"System prompt file not found for deletion: {filename}")
            return False

        try:
            file_path.unlink()
            logger.info(f"Deleted system prompt file: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete system prompt {filename}: {e}")
            return False

    def _load_system_prompt_info(self, file_path: Path) -> Optional[SystemPromptInfo]:
        """
        Load system prompt info from a file.

        Args:
            file_path: Path to the system prompt file

        Returns:
            SystemPromptInfo object or None if loading failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                logger.warning(f"System prompt file is empty: {file_path.name}")
                return None

            # Generate preview (first ~40 characters, clean up whitespace)
            preview = self._generate_preview(content)

            # Calculate word count
            word_count = len(content.split())

            return SystemPromptInfo(
                filename=file_path.name,
                content=content,
                preview=preview,
                word_count=word_count,
                file_path=file_path
            )

        except Exception as e:
            logger.error(f"Failed to load system prompt info from {file_path.name}: {e}")
            return None

    def _generate_preview(self, content: str, max_length: int = 40) -> str:
        """
        Generate a preview string from system prompt content.

        Args:
            content: Full system prompt content
            max_length: Maximum length of preview

        Returns:
            Preview string for display in tables
        """
        # Clean up content - remove excessive whitespace and newlines
        cleaned = ' '.join(content.split())

        if len(cleaned) <= max_length:
            return cleaned

        # Truncate at word boundary if possible
        truncated = cleaned[:max_length]
        last_space = truncated.rfind(' ')

        if last_space > max_length * 0.7:  # If we can break at a reasonable point
            return cleaned[:last_space] + "..."
        else:
            return cleaned[:max_length - 3] + "..."

    def ensure_prompts_directory(self) -> bool:
        """
        Ensure the system prompts directory exists.

        Returns:
            True if directory exists or was created successfully
        """
        try:
            self.prompts_dir.mkdir(exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create system prompts directory: {e}")
            return False

    def validate_system_prompt_content(self, content: str) -> bool:
        """
        Validate system prompt content.

        Args:
            content: System prompt content to validate

        Returns:
            True if content is valid for use as system prompt
        """
        if not content or not content.strip():
            return False

        # Basic validation - ensure it's not too long (reasonable limit for context)
        if len(content) > 10000:  # ~10k chars should be reasonable
            logger.warning("System prompt content is very long and may affect performance")
            return False

        return True
