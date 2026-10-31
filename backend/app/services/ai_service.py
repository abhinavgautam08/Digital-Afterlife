"""
AI and Ollama integration service.
Completely decoupled from route handlers.
Provides local model status, availability checks, and clear offline setup guidance.
Never downloads models silently or transmits user data externally.
"""
from typing import List, Dict, Any, Optional
import httpx

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.ai import AIStatusResponse, AIModelsResponse, ModelInfo


class OllamaService:
    def __init__(self, base_url: Optional[str] = None, configured_model: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.configured_model = configured_model or settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS

    def get_setup_instructions(self) -> str:
        return (
            "To enable local AI capabilities without internet access:\n"
            "1. Download and install Ollama from https://ollama.ai\n"
            "2. Start the Ollama background daemon on your machine.\n"
            f"3. In your terminal, pull the recommended open-weight model: ollama pull {self.configured_model}\n"
            f"4. Ensure Ollama is listening locally on {self.base_url}."
        )

    def check_status(self) -> AIStatusResponse:
        """
        Pings the local Ollama daemon and checks if the configured model is installed.
        Returns a rich status object; never raises uncaught network exceptions.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models_raw = data.get("models", [])
                    installed_model_names = [m.get("name", "") for m in models_raw]

                    # Check availability of configured model (support tags like qwen2.5:3b or qwen2.5:3b-instruct)
                    is_available = any(
                        self.configured_model.lower() in name.lower() or name.lower().startswith(self.configured_model.lower())
                        for name in installed_model_names
                    )

                    return AIStatusResponse(
                        status="online",
                        ollama_running=True,
                        configured_model=self.configured_model,
                        model_available=is_available,
                        base_url=self.base_url,
                        installed_models=installed_model_names,
                        message=(
                            f"Ollama is running. Configured model '{self.configured_model}' is "
                            f"{'ready for local inference.' if is_available else 'not found locally. Run: ollama pull ' + self.configured_model}"
                        ),
                        setup_instructions=None if is_available else self.get_setup_instructions()
                    )
        except Exception as e:
            logger.debug(f"Ollama health check unreachable: {e}")

        # Fallback when Ollama is offline or uninstalled
        return AIStatusResponse(
            status="offline",
            ollama_running=False,
            configured_model=self.configured_model,
            model_available=False,
            base_url=self.base_url,
            installed_models=[],
            message=f"Local Ollama daemon is offline or unreachable at {self.base_url}.",
            setup_instructions=self.get_setup_instructions()
        )

    def list_models(self) -> AIModelsResponse:
        """
        Lists all locally pulled models from the Ollama instance.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models_list: List[ModelInfo] = []
                    for item in data.get("models", []):
                        name = item.get("name", "")
                        is_cfg = self.configured_model.lower() in name.lower()
                        models_list.append(
                            ModelInfo(
                                name=name,
                                model=item.get("model", name),
                                size=item.get("size"),
                                modified_at=item.get("modified_at"),
                                is_configured=is_cfg
                            )
                        )
                    return AIModelsResponse(
                        models=models_list,
                        count=len(models_list),
                        configured_model=self.configured_model
                    )
        except Exception as e:
            logger.debug(f"Failed to list local Ollama models: {e}")

        return AIModelsResponse(
            models=[],
            count=0,
            configured_model=self.configured_model
        )


ai_service = OllamaService()

