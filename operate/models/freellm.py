import google.generativeai as genai
from google.generativeai import types
import asyncio
import json
import logging
import time
import re
import random
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# OpenRouter free models for fallback - free models in order of preference
OPENROUTER_MODELS = [
    {"name": "deepseek/deepseek-r1-0528:free", "rpm": 30},
    {"name": "google/gemini-2.5-pro-exp-03-25", "rpm": 15},
    {"name": "qwen/qwen3-235b-a22b:free", "rpm": 30},
]

class APIKeyManager:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.key_usage_count = {}
        self.key_last_used = {}
        self.key_rate_limited_until = {}
        self.rate_limit_delay = 60  # seconds to wait after rate limit
        self.min_interval = 1  # minimum seconds between uses of same key
        self.logger = logging.getLogger(__name__)

        # Initialize tracking for each key
        for key in api_keys:
            self.key_usage_count[key] = 0
            self.key_last_used[key] = 0
            self.key_rate_limited_until[key] = 0

    def get_available_keys(self) -> List[str]:
        """Get list of currently available (not rate limited) API keys"""
        current_time = time.time()
        available_keys = []

        for key in self.api_keys:
            # Skip if key is currently rate limited
            if current_time < self.key_rate_limited_until[key]:
                continue

            # Check minimum interval between uses
            if current_time - self.key_last_used[key] < self.min_interval:
                continue

            available_keys.append(key)

        return available_keys

    def get_next_key(self) -> str:
        """Get the next available API key with intelligent rotation"""
        current_time = time.time()
        best_key = None
        min_usage = float('inf')

        # Find the best available key based on usage and rate limits
        for i in range(len(self.api_keys)):
            key_index = (self.current_key_index + i) % len(self.api_keys)
            key = self.api_keys[key_index]

            # Skip if key is currently rate limited
            if current_time < self.key_rate_limited_until[key]:
                continue

            # Check minimum interval between uses
            if current_time - self.key_last_used[key] < self.min_interval:
                continue

            # Prefer key with lowest usage count
            if self.key_usage_count[key] < min_usage:
                best_key = key
                min_usage = self.key_usage_count[key]

        if best_key:
            self.current_key_index = (self.api_keys.index(best_key) + 1) % len(self.api_keys)
            self.key_last_used[best_key] = current_time
            self.key_usage_count[best_key] += 1
            self.logger.debug(f"Selected API key ending in ...{best_key[-8:]} (usage: {self.key_usage_count[best_key]})")
            return best_key

        # If no key available, wait and try again
        self.logger.warning("All API keys in use or rate limited - waiting before retry")
        time.sleep(2)
        return self.get_next_key()

    def mark_rate_limited(self, api_key: str):
        """Mark a key as rate limited and update tracking"""
        current_time = time.time()
        self.key_rate_limited_until[api_key] = current_time + self.rate_limit_delay
        self.key_last_used[api_key] = current_time  # Reset last used time
        self.logger.warning(f"API key ending in ...{api_key[-8:]} rate limited until {self.key_rate_limited_until[api_key]}")


class FreeLLMManager:
    def __init__(self, gemini_api_keys: List[str] = None, openrouter_api_keys: List[str] = None, model_configs: List[Dict] = None):
        # Initialize Gemini API key manager
        self.gemini_keys = gemini_api_keys or os.getenv("GOOGLE_API_KEYS", "").split(",") if os.getenv("GOOGLE_API_KEYS") else []
        self.gemini_keys = [key.strip() for key in self.gemini_keys if key.strip()]
        self.api_key_manager = APIKeyManager(self.gemini_keys) if self.gemini_keys else None

        # Default Gemini model configs (free tier models)
        self.model_configs = model_configs or [
            {"name": "gemini-2.5-pro", "rpm": 5},
            {"name": "gemini-2.5-flash", "rpm": 10},
            {"name": "gemini-2.5-flash-lite-preview-06-17", "rpm": 15},
            {"name": "gemini-2.0-flash", "rpm": 15},
            {"name": "gemini-2.0-flash-lite", "rpm": 30},
        ]
        self.current_model_config = self.model_configs[0]

        self.logger = logging.getLogger(__name__)
        self.clients = {}  # Cache clients for each API key
        self.model_request_counts = {} # Track requests per minute for each model
        for cfg in self.model_configs:
            self.model_request_counts[cfg['name']] = []

        # Initialize OpenRouter clients if OpenRouter keys are available
        self.openrouter_keys = openrouter_api_keys or os.getenv("OPENROUTER_API_KEYS", "").split(",") if os.getenv("OPENROUTER_API_KEYS") else []
        self.openrouter_keys = [key.strip() for key in self.openrouter_keys if key.strip()]
        self.openrouter_clients = {}
        self.openrouter_model_index = 0
        self.openrouter_request_counts = {}
        if self.openrouter_keys:
            self.logger.info(f"Initialized {len(self.openrouter_keys)} OpenRouter API keys")

        # Initialize OpenRouter clients for each key
        for key in self.openrouter_keys:
            self.openrouter_clients[key] = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=key,
            )

        # Initialize request tracking for OpenRouter models
        for model_config in OPENROUTER_MODELS:
            self.openrouter_request_counts[model_config['name']] = []

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('free_llm.log'),
                logging.StreamHandler()
            ]
        )

    def _get_client(self, api_key: str):
        """Get or create a client for the given API key using the current model configuration"""
        model_name = self.current_model_config['name']
        if api_key not in self.clients:
            self.clients[api_key] = {}

        if model_name not in self.clients[api_key]:
            genai.configure(api_key=api_key)
            self.clients[api_key][model_name] = genai.GenerativeModel(model_name)
        return self.clients[api_key][model_name]

    def _can_make_request(self) -> bool:
        """Check if a request can be made with the current model without exceeding RPM."""
        if not self.api_key_manager:
            return False

        model_name = self.current_model_config['name']
        rpm_limit = self.current_model_config['rpm']
        current_time = time.time()

        # Clean up old requests (older than 60 seconds)
        self.model_request_counts[model_name] = [
            t for t in self.model_request_counts.get(model_name, []) if current_time - t < 60
        ]

        if len(self.model_request_counts[model_name]) < rpm_limit:
            return True
        else:
            self.logger.warning(f"Model {model_name} RPM limit reached ({rpm_limit} RPM).")
            # Automatically switch to next model when limit reached
            self._switch_model()
            return False

    def _record_request(self):
        """Record a successful request for the current model."""
        model_name = self.current_model_config['name']
        self.model_request_counts[model_name].append(time.time())

    def _switch_model(self):
        """Switch to the next available model with proper cooldown."""
        current_model_index = self.model_configs.index(self.current_model_config)
        next_model_index = (current_model_index + 1) % len(self.model_configs)
        self.current_model_config = self.model_configs[next_model_index]

        # Reset request count for new model
        self.model_request_counts[self.current_model_config['name']] = []

        # Add cooldown period if previous model was rate limited
        cooldown = 5 if len(self.model_request_counts) > 1 else 0
        time.sleep(cooldown)

        self.logger.info(f"Switched to model: {self.current_model_config['name']} (RPM: {self.current_model_config['rpm']})")

    def _get_next_openrouter_model(self) -> Dict:
        """Get the next OpenRouter model in preference order."""
        model_config = OPENROUTER_MODELS[self.openrouter_model_index]
        self.openrouter_model_index = (self.openrouter_model_index + 1) % len(OPENROUTER_MODELS)
        return model_config

    def _can_make_openrouter_request(self, model_name: str) -> bool:
        """Check if a request can be made with the OpenRouter model without exceeding RPM."""
        current_time = time.time()

        # Clean up old requests (older than 60 seconds)
        self.openrouter_request_counts[model_name] = [
            t for t in self.openrouter_request_counts.get(model_name, []) if current_time - t < 60
        ]

        rpm_limit = next((model['rpm'] for model in OPENROUTER_MODELS if model['name'] == model_name), 30)
        if len(self.openrouter_request_counts[model_name]) < rpm_limit:
            return True
        else:
            self.logger.warning(f"OpenRouter model {model_name} RPM limit reached ({rpm_limit} RPM).")
            return False

    def _record_openrouter_request(self, model_name: str):
        """Record a successful OpenRouter request."""
        self.openrouter_request_counts[model_name].append(time.time())

    async def generate_content_with_fallback(self, prompt: str, image_path: str = None, max_retries: int = 3) -> str:
        """
        Generate content using Gemini primary with OpenRouter fallback.
        Returns the raw response text.
        """
        # First try Gemini
        for api_attempt in range(max_retries):
            try:
                if not self.api_key_manager:
                    break  # Skip Gemini if no keys

                # Check and switch model if RPM limit is reached
                if not self._can_make_request():
                    self._switch_model()
                    await asyncio.sleep(5)  # Wait a bit before trying again with the new model
                    continue

                # Get next API key
                api_key = self.api_key_manager.get_next_key()
                client = self._get_client(api_key)

                # Prepare content for Gemini
                if image_path:
                    # Load image for vision tasks
                    import PIL.Image
                    image = PIL.Image.open(image_path)
                    content = [prompt, image]
                else:
                    content = [prompt]

                # Make async API call
                response = await asyncio.to_thread(
                    client.generate_content,
                    contents=content
                )

                # Record the request regardless of the response
                self._record_request()

                # Parse response
                if response and response.text:
                    return response.text

                # Handle empty or invalid response
                self.logger.warning(f"Empty/invalid response from Gemini API for model {self.current_model_config['name']}")
                self._switch_model()
                await asyncio.sleep(5)
                continue

            except Exception as e:
                error_msg = str(e).lower()

                # Check for rate limit errors
                if 'rate limit' in error_msg or 'quota' in error_msg or '429' in error_msg:
                    self.api_key_manager.mark_rate_limited(api_key)
                    self.logger.warning("Gemini quota exceeded, switching API key...")
                    await asyncio.sleep(5)
                    continue

                # Check for timeout errors
                elif '504' in error_msg or 'deadline' in error_msg:
                    self._switch_model()
                    self.logger.warning(f"Timeout error, switched to model: {self.current_model_config['name']}")
                    await asyncio.sleep(5)
                    continue

                # Check for other API errors
                elif 'api' in error_msg or 'request' in error_msg:
                    self._switch_model()
                    self.logger.warning(f"API error, switched to model: {self.current_model_config['name']}")
                    await asyncio.sleep(3)
                    continue

                else:
                    # Non-API error, re-raise
                    raise e

        # If Gemini fails, try OpenRouter as fallback
        if self.openrouter_keys:
            self.logger.info("Switching to OpenRouter as fallback provider")

            max_total_attempts = 6  # Limit total attempts to prevent infinite loops
            attempts = 0

            # Try each OpenRouter model in order of preference
            for model_config in OPENROUTER_MODELS:
                if attempts >= max_total_attempts:
                    self.logger.warning(f"Reached maximum attempts ({max_total_attempts}), stopping OpenRouter fallback")
                    break

                model_name = model_config['name']

                # Check if we can make a request with this model
                if not self._can_make_openrouter_request(model_name):
                    self.logger.warning(f"OpenRouter model {model_name} rate limited, trying next model...")
                    continue

                # Try each available OpenRouter key with this model (max 2 keys per model)
                keys_tried = 0
                for openrouter_key in self.openrouter_keys:
                    if keys_tried >= 2 or attempts >= max_total_attempts:
                        break

                    keys_tried += 1
                    attempts += 1

                    try:
                        client = self.openrouter_clients[openrouter_key]

                        # Prepare messages for OpenRouter
                        messages = [{"role": "user", "content": prompt}]

                        # Add image if provided (OpenRouter vision support)
                        if image_path:
                            import base64
                            with open(image_path, "rb") as img_file:
                                img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

                            messages[0]["content"] = [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
                                }
                            ]

                        # Make OpenRouter API call with timeout
                        self.logger.info(f"Trying OpenRouter model {model_name} with key {openrouter_key[:10]}...")
                        response = await asyncio.wait_for(
                            asyncio.to_thread(
                                client.chat.completions.create,
                                model=model_name,
                                messages=messages,
                                max_tokens=4000,
                                temperature=0.7
                            ),
                            timeout=30.0  # 30 second timeout
                        )

                        # Record the successful request
                        self._record_openrouter_request(model_name)

                        # Parse OpenRouter response
                        if response and response.choices and len(response.choices) > 0:
                            response_text = response.choices[0].message.content
                            if response_text:
                                self.logger.info(f"Successfully generated content using OpenRouter model {model_name}")
                                return response_text

                    except asyncio.TimeoutError:
                        self.logger.warning(f"OpenRouter request timed out for {model_name}, trying next...")
                        continue
                    except Exception as e:
                        error_msg = str(e).lower()
                        # Check for rate limit errors
                        if 'rate limit' in error_msg or '429' in error_msg:
                            self.logger.warning(f"OpenRouter model {model_name} rate limited, trying next model...")
                            break  # Try next model instead of next key
                        else:
                            self.logger.warning(f"OpenRouter attempt failed for {model_name}: {str(e)[:100]}...")
                            continue

            self.logger.warning("All OpenRouter attempts also failed")

        # If we get here, all API attempts failed
        raise Exception("All free LLM providers failed - no response generated")
