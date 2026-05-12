#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Modified DI role for DataSciBench
@Modified by: 2024/8/6. Added a plan_list to capture the completed/failed plans.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Literal

from pydantic import Field, PrivateAttr, model_validator

from metagpt.actions.di.ask_review import ReviewConst
from metagpt.actions.di.execute_nb_code import ExecuteNbCode
from metagpt.actions.di.write_analysis_code import CheckData, WriteAnalysisCode
from metagpt.logs import logger
from metagpt.prompts.di.write_analysis_code import DATA_INFO
from metagpt.roles import Role
from metagpt.schema import Message, Task, TaskResult, Plan
from metagpt.strategy.task_type import TaskType
from metagpt.tools.tool_recommend import BM25ToolRecommender, ToolRecommender
from metagpt.utils.common import CodeParser

from metagpt.utils.cost_manager import Costs
from metagpt.config2 import Config
from .tame_config import TAMEConfig
from .tame_recovery import build_recovery_prompt, classify_failure
from .tame_runtime_state import (
    collect_artifact_status,
    read_json,
    rollback_artifacts,
    select_relevant_artifacts,
    snapshot_artifacts,
    write_json,
)

REACT_THINK_PROMPT = """
# User Requirement
{user_requirement}
# Context
{context}

Output a json following the format:
```json
{{
    "thoughts": str = "Thoughts on current situation, reflect on how you should proceed to fulfill the user requirement",
    "state": bool = "Decide whether you need to take more actions to complete the user requirement. Return true if you think so. Return false if you think the requirement has been completely fulfilled."
}}
```
"""


class SciDataInterpreter(Role):
    name: str = "SciAgent"
    profile: str = "DataInterpreter"
    auto_run: bool = True
    use_plan: bool = True
    use_reflection: bool = False
    execute_code: ExecuteNbCode = Field(default_factory=ExecuteNbCode, exclude=True)
    tools: list[str] = []  # Use special symbol ["<all>"] to indicate use of all registered tools
    tool_recommender: ToolRecommender = None
    react_mode: Literal["plan_and_act", "react"] = "plan_and_act"
    max_react_loop: int = 10  # used for react mode

    # For evaluation
    plan_list: list[Plan] = [] # a list of completed/failed plans, we can get the code and resutls from it
    cost_list: list[Costs] = [] # a list of costs for each (TODO:? not sure, might be the accumulated cost) plan
    step_error_counter_list: list[int] = [] # a temporary error counter for each plan
    error_counter_list: list[int] = [] # a list of error counter for each plan
    hard_retry: bool = False
    max_retry: int = 3
    tame_config: TAMEConfig = Field(default_factory=TAMEConfig)
    checkpoint_file: str = "tame_checkpoint.json"
    ledger_file: str = "tame_ledger.jsonl"
    progress_file: str = "tame_progress.json"
    artifact_state_file: str = "tame_artifacts.json"
    backup_root: str = ".tame_backups"
    _minimal_action_taken: bool = PrivateAttr(default=False)
    _executed_steps: int = PrivateAttr(default=0)
    _ledger: list[dict] = PrivateAttr(default_factory=list)
    _recovery_prompt: str = PrivateAttr(default="")
    # config: Config

    # def __init__(self, config):
    #     super().__init__(config)

    def update_results_for_eval(self, rsp: Plan):
        rsp_json = self.read_json_from_list(rsp)
        self.plan_list.append(rsp_json)
        self.cost_list.append(self.llm.cost_manager.get_costs())
        self.error_counter_list.append(self.step_error_counter_list)
        self.step_error_counter_list = []
        self._save_checkpoint(event="plan_finished")

    def update_react_results_for_eval(self, rsp: TaskResult):
        self.error_counter_list.append(self.step_error_counter_list)
        self._save_checkpoint(event="react_step_finished", task_result=rsp)

    def get_results_for_eval(self):
        return self.plan_list, self.cost_list, self.error_counter_list

    # helper func 1
    def read_json_from_list(self, plan):
        content = str(plan)
        # Remove any non-JSON content
        json_start_pos = content.find("## Current Plan")
        json_end_pos = content.find("## Current Task")
        content = content[json_start_pos+16:json_end_pos]
        json_objects = json.loads(content)
        return json_objects

    @model_validator(mode="after")
    def set_plan_and_tool(self) -> "Interpreter":
        if not self.tame_config.adaptation:
            self.react_mode = "react"
            self.use_reflection = False
        elif not self.tame_config.planning:
            self.react_mode = "react"
        else:
            self.react_mode = "plan_and_act"

        self.max_react_loop = self.tame_config.max_react_loop
        self.max_retry = self.tame_config.max_retry
        self._set_react_mode(react_mode=self.react_mode, max_react_loop=self.max_react_loop, auto_run=self.auto_run)
        self.use_plan = self.tame_config.planning and self.react_mode == "plan_and_act"
        if self.tools and self.tame_config.tool_selection and not self.tool_recommender:
            self.tool_recommender = BM25ToolRecommender(tools=self.tools)
        self.set_actions([WriteAnalysisCode])
        self._set_state(0)
        return self

    @property
    def working_memory(self):
        return self.rc.working_memory

    async def _think(self) -> bool:
        """Useful in 'react' mode. Use LLM to decide whether and what to do next."""
        if not self.tame_config.adaptation:
            if self._minimal_action_taken:
                self._set_state(-1)
                return False
            self._set_state(0)
            return True

        user_requirement = self.get_memories()[0].content
        context = self.working_memory.get()

        if not context:
            # just started the run, we need action certainly
            self.working_memory.add(self.get_memories()[0])  # add user requirement to working memory
            self._set_state(0)
            return True

        prompt = REACT_THINK_PROMPT.format(user_requirement=user_requirement, context=context)
        rsp = await self.llm.aask(prompt)
        try:
            rsp_dict = json.loads(CodeParser.parse_code(block=None, text=rsp, lang="json"))
        except Exception:
            logger.warning("React think expected JSON but received non-JSON output; continuing with one action.")
            self.working_memory.add(Message(content=str(rsp)[:1000], role="assistant"))
            self._set_state(0)
            return True
        self.working_memory.add(Message(content=rsp_dict["thoughts"], role="assistant"))
        need_action = rsp_dict["state"]
        self._set_state(0) if need_action else self._set_state(-1)

        return need_action

    async def _act(self) -> Message:
        """Useful in 'react' mode. Return a Message conforming to Role._act interface."""
        self._load_checkpoint()
        code, result, success = await self._write_and_exec_code()
        self._minimal_action_taken = True
        self.plan_list.append(
            [
                {
                    "task_id": "1",
                    "dependent_task_ids": [],
                    "instruction": "Solve the user requirement in one Observe-Think-Act step",
                    "task_type": "data analysis",
                    "code": code,
                    "result": result,
                    "is_success": success,
                    "is_finished": True,
                }
            ]
        )
        self.cost_list.append(self.llm.cost_manager.get_costs())
        self.error_counter_list.append(self.step_error_counter_list)
        self.step_error_counter_list = []
        self._save_checkpoint(event="react_finished")
        return Message(content=code, role="assistant", cause_by=WriteAnalysisCode)

    async def _plan_and_act(self) -> Message:
        try:
            self._load_checkpoint()
            rsp = await super()._plan_and_act()
            self.update_results_for_eval(rsp)
            await self.execute_code.terminate()
            return rsp
        except Exception as e:
            await self.execute_code.terminate()
            raise e

    async def _act_on_task(self, current_task: Task) -> TaskResult:
        """Useful in 'plan_and_act' mode. Wrap the output in a TaskResult for review and confirmation."""
        code, result, is_success = await self._write_and_exec_code(max_retry=self.max_retry)
        task_result = TaskResult(code=code, result=result, is_success=is_success)
        self.update_react_results_for_eval(task_result)
        return task_result

    async def _write_and_exec_code(self, max_retry: int = 3):
        counter = 0
        error_counter = -1
        success = False
        max_retry = self._effective_max_retry(max_retry)
        user_requirement = self.get_memories()[0].content
        expected_specs = self._parse_artifact_contract(user_requirement)

        # plan info
        plan_status = self.planner.get_plan_status() if self.tame_config.planning and self.use_plan else ""

        # tool info
        if self.tame_config.tool_selection and self.tool_recommender:
            context = (
                self.working_memory.get()[-1].content if self.working_memory.get() else ""
            )  # thoughts from _think stage in 'react' mode
            plan = self.planner.plan if self.use_plan else None
            tool_info = await self.tool_recommender.get_recommended_tool_info(context=context, plan=plan)
        else:
            tool_info = ""

        # data info
        if self.tame_config.check_data:
            await self._check_data()

        self._recovery_prompt = ""
        while not success and counter < max_retry:
            final_guard_triggered = False
            ### write code ###
            code, cause_by = await self._write_code(counter, plan_status, tool_info)
            code = self._prepare_code_for_execution(code)
            relevant_specs = select_relevant_artifacts(expected_specs, code) if self.tame_config.maintenance else {}
            artifact_snapshot = (
                snapshot_artifacts(
                    list(relevant_specs.keys()),
                    self.backup_root,
                    f"step_{self._executed_steps + 1}_retry_{counter}",
                )
                if relevant_specs
                else {}
            )
            self._write_progress(
                phase="generated",
                retry_index=counter,
                success=False,
                error_type="",
                result_preview="",
                artifact_status=collect_artifact_status(relevant_specs) if relevant_specs else {},
            )

            if self.tame_config.working_memory:
                self.working_memory.add(Message(content=code, role="assistant", cause_by=cause_by))

            ### execute code ###
            verified, verification_msg = self._verify_code(code)
            if verified:
                result, success = await self.execute_code.run(code)
                if success:
                    artifact_ok, artifact_msg = self._verify_artifact_contract(code)
                    if not artifact_ok:
                        result = f"{result}\n\nT_plus artifact contract check failed:\n{artifact_msg}"
                        success = False
                    elif self.tame_config.final_guard and self._requires_final_answer(user_requirement) and not self._final_answer_ok():
                        result = f"{result}\n\nTAME final artifact guard failed: final_answer.txt is missing or empty."
                        success = False
                        final_guard_triggered = True
            else:
                result, success = verification_msg, False

            artifact_status = collect_artifact_status(relevant_specs) if relevant_specs else {}
            signal = classify_failure(result) if not success else None
            error_type = "missing_final_answer" if final_guard_triggered else (signal.error_type if signal else "")

            if not success and self.tame_config.maintenance and artifact_snapshot:
                rollback_artifacts(artifact_snapshot)
                artifact_status = collect_artifact_status(relevant_specs)

            self._write_artifact_state(artifact_status)
            self._write_progress(
                phase="verified" if success else "failed",
                retry_index=counter,
                success=success,
                error_type=error_type,
                result_preview=str(result)[:1000],
                artifact_status=artifact_status,
            )

            if self.tame_config.working_memory:
                self.working_memory.add(Message(content=result, role="user", cause_by=ExecuteNbCode))
            self._record_step(
                code=code,
                result=result,
                success=success,
                retry_index=counter,
                error_type=error_type,
                artifact_status=artifact_status,
            )

            ### process execution result ###
            counter += 1
            error_counter += 1

            if not success and final_guard_triggered and self.tame_config.final_guard and counter < max_retry:
                self._recovery_prompt = self._build_final_guard_prompt(result)
            elif not success and self.tame_config.recovery and counter < max_retry:
                signal = signal or classify_failure(result)
                missing_artifacts = list((artifact_status or {}).get("missing_paths", []))
                missing_artifacts.extend(
                    item["path"]
                    for item in (artifact_status or {}).get("schema_errors", [])
                    if item["path"] not in missing_artifacts
                )
                self._recovery_prompt = build_recovery_prompt(signal, result, missing_artifacts, counter)
            else:
                self._recovery_prompt = ""

            if not success and counter >= max_retry and self.tame_config.recovery and not self.hard_retry:
                logger.info("coding failed; non-interactive benchmark mode records the failed attempt without human review.")

        self.step_error_counter_list.append(error_counter)
        return code, result, success

    async def _write_code(
        self,
        counter: int,
        plan_status: str = "",
        tool_info: str = "",
    ):
        todo = self.rc.todo  # todo is WriteAnalysisCode
        logger.info(f"ready to {todo.name}")
        use_reflection = counter > 0 and self.use_reflection and self.tame_config.reflection

        user_requirement = self.get_memories()[0].content
        print("!!!Requirement:\n\n", user_requirement)

        code = await todo.run(
            user_requirement=user_requirement,
            plan_status=plan_status,
            tool_info=tool_info,
            working_memory=self._prompt_working_memory(),
            use_reflection=use_reflection,
        )

        return code, todo

    async def _check_data(self):
        if (
            not self.use_plan
            or not self.planner.plan.get_finished_tasks()
            or self.planner.plan.current_task.task_type
            not in [
                TaskType.DATA_PREPROCESS_CLEANING.type_name,
                TaskType.PREDICTIVE_MODELING.type_name,
                # TaskType.DATA_MINING.type_name,
                TaskType.PATTERN_RECOGNITION.type_name,
            ]
        ):
            return
        logger.info("Check updated data")
        code = await CheckData().run(self.planner.plan)
        if not code.strip():
            return
        result, success = await self.execute_code.run(code)
        if success:
            data_info = DATA_INFO.format(info=result)
            self.working_memory.add(Message(content=data_info, role="user", cause_by=CheckData))

    def _prompt_working_memory(self):
        messages = []
        if self.tame_config.working_memory:
            messages.extend(self.working_memory.get())
        if self.tame_config.maintenance and self._ledger:
            summary = json.dumps(self._ledger[-3:], ensure_ascii=False)
            messages.append(Message(content=f"Runtime ledger summary: {summary}", role="user"))
        if (self.tame_config.recovery or self.tame_config.final_guard) and self._recovery_prompt:
            messages.append(Message(content=self._recovery_prompt, role="user"))
        return messages

    def _effective_max_retry(self, requested_retry: int) -> int:
        if self.tame_config.adaptation or self.tame_config.recovery or self.tame_config.final_guard:
            return max(1, min(requested_retry, self.tame_config.max_retry))
        return 1

    def _requires_final_answer(self, user_requirement: str) -> bool:
        return "final_answer.txt" in user_requirement

    def _final_answer_ok(self) -> bool:
        try:
            with open("final_answer.txt", "r", encoding="utf-8") as reader:
                return bool(reader.read().strip())
        except OSError:
            return False

    def _build_final_guard_prompt(self, result: str) -> str:
        result_excerpt = str(result)[-1200:]
        return (
            "## TAME Final Artifact Guard\n"
            "The previous code executed, but the required final artifact is missing or empty.\n"
            "Do not redo broad exploration unless necessary. Use the staged local files and the prior execution result to write `final_answer.txt`.\n"
            "`final_answer.txt` must contain only the final answer string, with no explanation, markdown, or extra whitespace.\n"
            "If the question genuinely has no applicable answer, write exactly `Not Applicable`.\n\n"
            f"Previous execution result excerpt:\n{result_excerpt}"
        )

    def _prepare_code_for_execution(self, code: str) -> str:
        """Minimal E_core adapter: make single-shot generated code executable.

        This is intentionally deterministic and model-independent. It does not
        add planning or repair; it only provides common imports and exposes task
        input files from the parent task directory to the run directory.
        """
        prelude = r'''
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

_INPUT_SUFFIXES = {
    ".csv", ".xlsx", ".xls", ".json", ".md", ".parquet", ".txt",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp",
    ".npy", ".pkl",
}
_parent = Path("..")
if _parent.exists():
    for _src in _parent.iterdir():
        if _src.is_file() and _src.suffix.lower() in _INPUT_SUFFIXES:
            _dst = Path(_src.name)
            if not _dst.exists():
                shutil.copy2(_src, _dst)
'''
        return prelude.strip() + "\n\n" + code.strip()

    def _verify_code(self, code: str) -> tuple[bool, str]:
        if self.tame_config.budget and self._executed_steps >= self.tame_config.max_steps:
            return False, f"T_plus budget verifier blocked execution: max_steps={self.tame_config.max_steps}"
        if not self.tame_config.verifier:
            return True, ""

        blocked_patterns = [
            "shutil.rmtree",
            "os.remove",
            "os.rmdir",
            "subprocess.",
            "os.system",
            "rm -rf",
            "del /",
            "mkfs",
            "open('/",
            'open("/',
            "pip install",
            "!pip",
        ]
        lowered = code.lower()
        for pattern in blocked_patterns:
            if pattern in lowered:
                return False, f"T_plus verifier blocked potentially unsafe code pattern: {pattern}"
        return True, ""

    def _verify_artifact_contract(self, code: str) -> tuple[bool, str]:
        if not self.tame_config.t_plus:
            return True, ""

        user_requirement = self.get_memories()[0].content
        specs = self._parse_artifact_contract(user_requirement)
        if not specs:
            return True, ""

        errors = []
        relevant_specs = {
            path: columns
            for path, columns in specs.items()
            if path in code or os.path.basename(path) in code
        }
        if not relevant_specs:
            return True, ""

        for path, columns in relevant_specs.items():
            if not os.path.exists(path):
                errors.append(f"Missing required artifact: {path}")
                continue
            if columns and path.lower().endswith(".csv"):
                try:
                    import pandas as pd

                    df = pd.read_csv(path, nrows=5)
                    missing = [col for col in columns if col not in df.columns]
                    if missing:
                        errors.append(
                            f"Artifact {path} is missing required columns: {missing}; existing columns: {list(df.columns)}"
                        )
                except Exception as e:
                    errors.append(f"Could not inspect CSV artifact {path}: {e}")

        if errors:
            return False, "\n".join(errors)
        return True, ""

    def _parse_artifact_contract(self, requirement: str) -> dict[str, list[str]]:
        marker = "## TAME Artifact Contract"
        if marker not in requirement:
            return {}

        section = requirement.split(marker, 1)[1]
        next_section = re.search(r"\n##\s+", section)
        if next_section:
            section = section[: next_section.start()]

        specs: dict[str, list[str]] = {}
        saw_contract_item = False
        for line in section.splitlines():
            if saw_contract_item and not line.strip():
                break
            match = re.match(r"\s*-\s+`(?P<path>[^`]+)`:(?P<rest>.*)$", line)
            if not match:
                continue
            saw_contract_item = True
            path = match.group("path")
            rest = match.group("rest")
            columns = re.findall(r"`([^`]+)`", rest) if "required columns:" in rest else []
            specs[path] = columns
        return specs

    def _record_step(
        self,
        code: str,
        result: str,
        success: bool,
        retry_index: int,
        error_type: str = "",
        artifact_status: dict | None = None,
    ):
        self._executed_steps += 1
        item = {
            "ts": time.time(),
            "variant": self.tame_config.variant,
            "step": self._executed_steps,
            "phase": "verified" if success else "failed",
            "retry_index": retry_index,
            "success": success,
            "error_type": error_type,
            "artifacts_expected": (artifact_status or {}).get("expected_paths", []),
            "artifacts_present": (artifact_status or {}).get("present_paths", []),
            "artifacts_missing": (artifact_status or {}).get("missing_paths", []),
            "schema_errors": (artifact_status or {}).get("schema_errors", []),
            "code_preview": code[:500],
            "result_preview": str(result)[:1000],
        }
        if self.tame_config.artifact_ledger:
            self._ledger.append(item)
            with open(self.ledger_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        self._save_checkpoint(event="step_finished")

    def _save_checkpoint(self, event: str, task_result: TaskResult = None):
        if not self.tame_config.checkpoint:
            return
        checkpoint = {
            "event": event,
            "variant": self.tame_config.variant,
            "layers": self.tame_config.as_layer_dict(),
            "executed_steps": self._executed_steps,
            "ledger": self._ledger[-20:],
            "progress_file": self.progress_file,
            "artifact_state_file": self.artifact_state_file,
            "error_counter_list": self.error_counter_list,
            "step_error_counter_list": self.step_error_counter_list,
        }
        if task_result:
            checkpoint["last_task_result"] = task_result.model_dump()
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    def _load_checkpoint(self):
        if not self.tame_config.resume or not os.path.exists(self.checkpoint_file):
            return
        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
            self._executed_steps = checkpoint.get("executed_steps", 0)
            self._ledger = checkpoint.get("ledger", [])
            progress = read_json(self.progress_file) if self.tame_config.maintenance else {}
            self._recovery_prompt = progress.get("recovery_prompt", "")
        except Exception as e:
            logger.warning(f"Failed to load TAME checkpoint: {e}")

    def _write_progress(
        self,
        phase: str,
        retry_index: int,
        success: bool,
        error_type: str,
        result_preview: str,
        artifact_status: dict,
    ):
        if not self.tame_config.maintenance:
            return
        payload = {
            "variant": self.tame_config.variant,
            "step": self._executed_steps + 1,
            "phase": phase,
            "retry_index": retry_index,
            "success": success,
            "error_type": error_type,
            "result_preview": result_preview,
            "artifact_status": artifact_status,
            "recovery_prompt": self._recovery_prompt,
        }
        write_json(self.progress_file, payload)

    def _write_artifact_state(self, artifact_status: dict):
        if not self.tame_config.maintenance:
            return
        payload = {
            "variant": self.tame_config.variant,
            "step": self._executed_steps + 1,
            "artifact_status": artifact_status,
        }
        write_json(self.artifact_state_file, payload)
