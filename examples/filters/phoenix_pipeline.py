"""
title: Phoenix Filter Pipeline
author: jia.deng@cloudkitchens.com
date: 2025-09-04
version: 1.0
license: MIT
description: A pipeline for Phoenix integration
requirements: arize-phoenix-otel
"""

from typing import List, Optional
from pydantic import BaseModel
import os

import phoenix.otel

class Pipeline:
    class Valves(BaseModel):
        # List target pipeline ids (models) that this filter will be connected to.
        # If you want to connect this filter to all pipelines, you can set pipelines to ["*"]
        # e.g. ["llama3:latest", "gpt-3.5-turbo"]
        pipelines: List[str] = []

        # Assign a priority level to the filter pipeline.
        # The priority level determines the order in which the filter pipelines are executed.
        # The lower the number, the higher the priority.
        priority: int = 0

    def __init__(self):
        # Pipeline filters are only compatible with Open WebUI
        # You can think of filter pipeline as a middleware that can be used to edit the form data before it is sent to the OpenAI API.
        self.type = "filter"

        # Optionally, you can set the id and name of the pipeline.
        # Best practice is to not specify the id so that it can be automatically inferred from the filename, so that users can install multiple versions of the same pipeline.
        # The identifier must be unique across all pipelines.
        # The identifier must be an alphanumeric string that can include underscores or hyphens. It cannot contain spaces, special characters, slashes, or backslashes.
        # self.id = "phoenix_filter_pipeline"
        self.name = "Phoenix Filter"

        # Initialize
        self.valves = self.Valves(
            **{
                "pipelines": ["*"],  # Connect to all pipelines
            }
        )

        self.tracer = None

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup: {__name__}")
        self._set_tracer()

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        print(f"on_shutdown: {__name__}")

    async def on_valves_updated(self):
        # This function is called when the valves are updated.
        print(f"on_valves_updated: {__name__}")
        # reset tracer
        self._set_tracer()

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        # This filter is applied to the form data before it is sent to the OpenAI API.
        print(f"inlet: {__name__}")

        if self.tracer is None:
            print("[WARNING] tracer is initialized")
            return body

        print(f"Inlet function called with body: {body} and user: {user}")

        user_message = body["messages"][-1]["content"]
        with self.tracer.start_as_current_span("inlet") as span:
            span.set_attribute("user.id", user.get("id", "unknown") if user else "unknown")
            span.set_attribute("user_message.length", len(user_message))
            span.set_attribute("user_message.content", user_message[:100])

        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"outlet: {__name__}")

        if self.tracer is None:
            print("[WARNING] tracer is initialized")
            return body

        print(f"Outlet function called with body: {body} and user: {user}")

        with self.tracer.start_as_current_span("outlet") as span:
            span.set_attribute("user.id", user.get("id", "unknown") if user else "unknown")

        return body

    def _set_tracer(self) -> None:

        tracer_provider = phoenix.otel.register(
            project_name=os.getenv("PHOENIX_PROJECT_NAME", "open-webui-pipelines"),
            endpoint=os.getenv(
                "PHOENIX_ENDPOINT",
                "http://phoenix.phoenix.svc.cluster.local/v1/traces",
            ),
            auto_instrument=True,
            set_global_tracer_provider=False,
            batch=True,
        )

        self.tracer = tracer_provider.get_tracer(__name__)