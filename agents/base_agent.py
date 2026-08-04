"""
agents/base_agent.py
====================
Scratchpad, Entry dataclass, and SpecialistAgent base class.
All three specialist agents inherit from SpecialistAgent.
Extracted from notebook v8.0 Steps 7 & 9.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from services.mistral_service import get_mistral_service
from app.config import AGENT_MAX_STEPS


# ══════════════════════════════════════════════════════════════════════════
#  SCRATCHPAD — typed ReAct trace (thought / action / observation)
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class Entry:
    role:    str        # "thought" | "action" | "observation"
    content: Any
    tool_id: str = ""
    ts:      float = field(default_factory=time.time)

    def to_str(self) -> str:
        if self.role == "thought":
            return f"THOUGHT: {self.content}"
        if self.role == "action":
            name = self.content.get("name", "?")
            args = json.dumps(self.content.get("args", {}), default=str)
            return f"ACTION:  {name}({args})"
        obs = json.dumps(self.content, default=str)
        return f"OBSERVATION: {obs[:500]}{'…' if len(obs) > 500 else ''}"


class Scratchpad:
    """Typed ReAct scratchpad — stores thoughts, actions, and observations."""

    def __init__(self):
        self._entries: List[Entry] = []
        self._counter = 0

    def _next_tid(self) -> str:
        self._counter += 1
        return f"call_{self._counter}"

    def add_thought(self, text: str):
        self._entries.append(Entry("thought", text))

    def add_action(self, name: str, args: dict) -> str:
        tid = self._next_tid()
        self._entries.append(Entry("action", {"name": name, "args": args}, tool_id=tid))
        return tid

    def add_observation(self, result: Any, tool_id: str = "", tool_name: str = ""):
        self._entries.append(Entry("observation", result, tool_id=tool_id))

    def tool_calls(self) -> List[str]:
        return [e.content["name"] for e in self._entries if e.role == "action"]

    def to_text(self, max_entries: int = 80) -> str:
        return "\n".join(e.to_str() for e in self._entries[-max_entries:])

    def to_messages(self, max_pairs: int = 18) -> list:
        """Convert scratchpad to Mistral message format for context injection."""
        msgs = []
        actions = [(i, e) for i, e in enumerate(self._entries) if e.role == "action"]
        recent_actions = actions[-max_pairs:]
        if not recent_actions:
            return []
        thought_entries = [e for e in self._entries if e.role == "thought"]
        if thought_entries:
            combined = "\n".join(e.content for e in thought_entries[-3:])
            msgs.append({"role": "assistant", "content": f"Reasoning so far:\n{combined}"})
        for idx, act in recent_actions:
            tool_name = act.content["name"]
            tool_args = act.content["args"]
            tid = act.tool_id
            msgs.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tid,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args, default=str),
                    },
                }],
            })
            obs_entries = [
                e for e in self._entries[idx + 1:]
                if e.role == "observation" and e.tool_id == tid
            ]
            obs_content = obs_entries[0].content if obs_entries else {}
            obs_str = json.dumps(obs_content, default=str)
            msgs.append({
                "role": "tool",
                "tool_call_id": tid,
                "name": tool_name,
                "content": obs_str[:2000],
            })
        return msgs


# ══════════════════════════════════════════════════════════════════════════
#  SPECIALIST AGENT BASE CLASS
# ══════════════════════════════════════════════════════════════════════════

class SpecialistAgent:
    """
    Single-purpose ReAct agent with a fixed tool set.
    Called by the Orchestrator with a specific sub-goal.
    Returns a structured result dict to the Orchestrator.
    """

    def __init__(
        self,
        name:          str,
        system_prompt: str,
        tool_registry: Dict[str, Callable],
        tool_schemas:  List[dict],
        max_steps:     int = AGENT_MAX_STEPS,
        verbose:       bool = True,
    ):
        self.name          = name
        self.system_prompt = system_prompt
        self.tool_registry = tool_registry
        self.tool_schemas  = tool_schemas
        self.max_steps     = max_steps
        self.verbose       = verbose
        self._svc          = get_mistral_service()

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [{self.name[:4].upper()}] {msg}")

    def run(self, task: str, context: str = "") -> Dict:
        """
        Execute a task using ReAct (Reason + Act) loop.
        Returns dict: result, steps, tool_calls, tools_used, scratch_text, scratch.
        """
        scratch   = Scratchpad()
        done      = False
        step_n    = 0
        final_out = {}

        self._log(f"▶ Task: {task[:80]}")

        while not done and step_n < self.max_steps:
            step_n += 1

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": f"TASK: {task}\n\nCONTEXT FROM ORCHESTRATOR:\n{context or 'None'}"},
            ]
            messages.extend(scratch.to_messages(max_pairs=12))
            messages.append({
                "role": "user",
                "content": (
                    f"Step {step_n}/{self.max_steps}. "
                    f"Tools used so far: {list(dict.fromkeys(scratch.tool_calls()))}. "
                    "Call the next most useful tool, or finish() when your task is complete."
                ),
            })

            # max_tokens raised from 1000 to 2200 — when an agent calls
            # finish(report=...), the full report text is generated as
            # part of THIS SAME response (it's a tool-call argument), so
            # a low cap here truncates long reports mid-sentence. 2200
            # comfortably fits a full executive report + the tool-call
            # JSON wrapper around it.
            raw  = self._svc.chat(messages, tools=self.tool_schemas, tool_choice="auto", max_tokens=2200)
            msg  = raw["choices"][0]["message"]
            tcs  = msg.get("tool_calls") or []
            text = (msg.get("content") or "").strip()

            if text:
                scratch.add_thought(text)
                self._log(f"💭 {text[:120]}")

            if not tcs:
                # No tool call in this response. If the agent has already
                # made at least one real tool call earlier in this run,
                # a response with no tool call is the model saying "I'm
                # done" — stop instead of burning the remaining step
                # budget asking it to repeat itself in plain text.
                # (If it hasn't called any tool yet, this might just be
                # an upfront planning turn, so keep going as before.)
                if step_n >= self.max_steps or scratch.tool_calls():
                    done = True
                continue

            for tc in tcs:
                tname = tc["function"]["name"]
                try:
                    targs = json.loads(tc["function"]["arguments"])
                except Exception:
                    targs = {}

                tid = scratch.add_action(tname, targs)
                self._log(f"🔧 {tname}({list(targs.values())[:2]})")

                fn = self.tool_registry.get(tname)
                if fn:
                    try:
                        result = fn(**targs)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Tool {tname} not in registry."}

                scratch.add_observation(result, tool_id=tid, tool_name=tname)
                preview = json.dumps(result, default=str)[:200]
                self._log(f"📊 {preview}{'…' if len(json.dumps(result, default=str)) > 200 else ''}")

                if tname == "finish":
                    final_out = result
                    done = True
                    break

        return {
            "agent":        self.name,
            "task":         task,
            "result":       final_out,
            "steps":        step_n,
            "tool_calls":   len(scratch.tool_calls()),
            "tools_used":   list(dict.fromkeys(scratch.tool_calls())),
            "scratch_text": scratch.to_text(max_entries=60),
            "scratch":      scratch,
        }
