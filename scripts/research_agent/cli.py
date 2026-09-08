"""Create, run, inspect and resume a local research agent."""

import argparse
import json
import os
import sys
from pathlib import Path

from .core import Study
from .runner import api_model, run


def model_options(parser):
    parser.add_argument(
        "--provider", choices=["openai-responses", "openai-compatible", "ollama"], default="openai-responses"
    )
    parser.add_argument("--endpoint", default=os.getenv("RESEARCH_AI_ENDPOINT", "https://api.openai.com/v1"))
    parser.add_argument("--model", default=os.getenv("RESEARCH_AI_MODEL", ""))
    parser.add_argument("--api-key-env", default="RESEARCH_AI_API_KEY")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("init")
    create.add_argument("root", type=Path)
    create.add_argument("slug")
    create.add_argument("--objective", required=True)
    create.add_argument("--domain", choices=["mathematics", "statistics", "finance"], default="mathematics")
    create.add_argument("--contract", type=Path, help="optional exact tool/arguments/status JSON")
    create.add_argument("--network", action="store_true", help="allow scholarly metadata retrieval")
    for name in ("context", "status", "pause", "resume", "export", "inspect", "submit", "asset", "run"):
        command = commands.add_parser(name)
        command.add_argument("study", type=Path)
        if name == "inspect":
            command.add_argument("action_id", type=int)
        if name in {"submit", "asset"}:
            command.add_argument("file", type=Path)
        if name == "submit":
            command.add_argument("--revision", type=int, required=True)
            command.add_argument("--timeout", type=float, default=30)
        if name == "asset":
            command.add_argument("--label", required=True)
        if name == "export":
            command.add_argument("--output", type=Path, required=True)
        if name == "run":
            model_options(command)
            command.add_argument("--steps", type=int, default=12)
            command.add_argument("--seconds", type=float, default=600)
            command.add_argument("--tool-timeout", type=float, default=30)
    for name in ("serve", "mcp"):
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, default=Path(os.getenv("RESEARCH_AGENT_ROOT", "research-studies")))
        if name == "serve":
            command.add_argument("--port", type=int, default=8765)
            model_options(command)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            contract = json.loads(args.contract.read_text(encoding="utf-8")) if args.contract else None
            study = Study.create(args.root, args.slug, args.objective, args.domain, contract, args.network)
            result = {"directory": str(study.directory), **study.state()}
        elif args.command == "mcp":
            from .mcp_server import serve

            serve(args.root)
            return 0
        elif args.command == "serve":
            from .web import serve

            serve(
                args.root,
                args.port,
                api_model(args.provider, args.endpoint, args.model, args.api_key_env) if args.model else None,
            )
            return 0
        else:
            study = Study(args.study)
            if args.command == "run":
                if not args.model.strip():
                    raise ValueError("select a model with --model or RESEARCH_AI_MODEL")
                result = run(
                    study,
                    api_model(args.provider, args.endpoint, args.model, args.api_key_env),
                    args.steps,
                    args.seconds,
                    args.tool_timeout,
                )
            elif args.command == "submit":
                result = study.submit(json.loads(args.file.read_text(encoding="utf-8")), args.revision, args.timeout)
            elif args.command == "asset":
                result = study.add_asset(args.label, json.loads(args.file.read_text(encoding="utf-8")))
            elif args.command == "inspect":
                result = study.inspect(args.action_id)
            elif args.command in {"pause", "resume"}:
                result = study.pause(args.command == "pause")
            elif args.command == "export":
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(study.export(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                result = {"output": str(args.output)}
            else:
                result = study.context() if args.command == "context" else study.state()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return (
            1
            if result.get("stop_reason") in {"MODEL_ERROR", "REPEATED_FAILURE", "INTERRUPTED"}
            or result.get("execution") in {"FAILED", "TIMEOUT"}
            else 0
        )
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
