"""Pure helpers for synchronizing Upload Agent checkbox state."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def agent_checkbox_key(agent_id: str) -> str:
    return f"agent_cb_{agent_id}"


def build_agent_checkbox_state(agent_order: Iterable[str], selected_agents: Iterable[str]) -> dict[str, bool]:
    selected = set(selected_agents)
    return {agent_checkbox_key(agent_id): agent_id in selected for agent_id in agent_order}


def selected_agents_from_checkbox_state(
    agent_order: Iterable[str],
    state: Mapping[str, object],
) -> list[str]:
    return [agent_id for agent_id in agent_order if bool(state.get(agent_checkbox_key(agent_id), False))]
