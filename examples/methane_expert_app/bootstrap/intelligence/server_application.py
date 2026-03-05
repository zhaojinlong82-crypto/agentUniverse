# !/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
from pathlib import Path

from agentuniverse.agent_serve.web.web_booster import start_web_server
from agentuniverse.base.agentuniverse import AgentUniverse


class ServerApplication:
    @classmethod
    def start(cls):
        app_root = Path(__file__).resolve().parents[2]
        project_root = app_root.parents[1]
        examples_root = project_root / "examples"
        if str(examples_root) not in sys.path:
            sys.path.insert(0, str(examples_root))

        config_path = app_root / "config" / "config.toml"
        AgentUniverse().start(config_path=str(config_path), core_mode=True)
        start_web_server()


if __name__ == "__main__":
    ServerApplication.start()
