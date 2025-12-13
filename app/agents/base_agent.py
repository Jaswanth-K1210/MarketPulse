"""
Base Agent Class
Foundation for all specialized agents in the multi-agent system
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents"""

    def __init__(self, name: str, description: str):
        """
        Initialize base agent

        Args:
            name: Agent name
            description: Agent purpose/description
        """
        self.name = name
        self.description = description
        self.created_at = datetime.now()
        logger.info(f"✓ {self.name} initialized: {self.description}")

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method - must be implemented by each agent

        Args:
            input_data: Input data for processing

        Returns:
            Processed output data
        """
        pass

    def validate_input(self, input_data: Dict[str, Any], required_keys: list) -> bool:
        """
        Validate that input has required keys

        Args:
            input_data: Input to validate
            required_keys: List of required keys

        Returns:
            True if valid, False otherwise
        """
        missing = [key for key in required_keys if key not in input_data]
        if missing:
            logger.error(f"{self.name}: Missing required keys: {missing}")
            return False
        return True

    def log_action(self, action: str, details: Optional[str] = None):
        """
        Log agent action

        Args:
            action: Action performed
            details: Optional details
        """
        msg = f"[{self.name}] {action}"
        if details:
            msg += f": {details}"
        logger.info(msg)

    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle errors gracefully

        Args:
            error: Exception that occurred
            context: Context where error occurred

        Returns:
            Error response dict
        """
        error_msg = f"{self.name} error"
        if context:
            error_msg += f" in {context}"
        error_msg += f": {str(error)}"

        logger.error(error_msg)

        return {
            "success": False,
            "error": str(error),
            "agent": self.name,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

    def __str__(self) -> str:
        """String representation"""
        return f"{self.name} ({self.description})"

    def __repr__(self) -> str:
        """Debug representation"""
        return f"<{self.__class__.__name__}(name='{self.name}')>"
