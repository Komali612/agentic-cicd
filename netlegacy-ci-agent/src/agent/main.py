"""FROZEN entrypoint — start the HTTP service for this agent."""
from agent_core import runtime

from .agent import build_agent


def main() -> None:
    runtime.run(build_agent())


if __name__ == "__main__":
    main()
