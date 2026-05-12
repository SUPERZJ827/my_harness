# -*- encoding: utf-8 -*-
"""
@Date    :   2023/11/20 13:19:39
@Author  :   orange-crow
@File    :   write_analysis_code.py
"""
from __future__ import annotations

import json
import re

from metagpt.actions import Action
from metagpt.prompts.di.write_analysis_code import (
    CHECK_DATA_PROMPT,
    DEBUG_REFLECTION_EXAMPLE,
    INTERPRETER_SYSTEM_MSG,
    REFLECTION_PROMPT,
    REFLECTION_SYSTEM_MSG,
    STRUCTUAL_PROMPT,
)
from metagpt.schema import Message, Plan
from metagpt.utils.common import CodeParser, remove_comments


def parse_python_code_lenient(rsp: str) -> str:
    try:
        return CodeParser.parse_code(block=None, text=rsp)
    except Exception:
        # Some providers occasionally truncate the closing fence. Treat the
        # partial fenced body as code so execution fails in-band and the
        # benchmark records a failed run instead of aborting the harness.
        for marker in ("```python", "```py", "```"):
            if marker in rsp:
                body = rsp.split(marker, 1)[1]
                return body.split("```", 1)[0].strip()
        return rsp.strip()


def parse_reflection_impl_lenient(rsp: str) -> str:
    # Prefer the legacy reflection JSON format when present, because older
    # running prompts may still return {"reflection": ..., "improved_impl": ...}.
    try:
        reflect_dict = CodeParser.parse_code(block=None, lang="json", text=rsp)
        return json.loads(reflect_dict)["improved_impl"]
    except Exception:
        pass

    # Fallback for malformed/truncated JSON strings that still contain an
    # improved_impl field. This keeps the run in-band instead of aborting.
    match = re.search(r'"improved_impl"\s*:\s*"(?P<code>.*)', rsp, flags=re.DOTALL)
    if match:
        code = match.group("code")
        code = code.rsplit('"\n}', 1)[0]
        code = code.rsplit('"\r\n}', 1)[0]
        code = code.rsplit('"\n```', 1)[0]
        code = code.rsplit('"\r\n```', 1)[0]
        try:
            return bytes(code, "utf-8").decode("unicode_escape")
        except Exception:
            return code.replace("\\n", "\n").replace('\\"', '"')

    return parse_python_code_lenient(rsp)


class WriteAnalysisCode(Action):
    async def _debug_with_reflection(self, context: list[Message], working_memory: list[Message]):
        reflection_prompt = REFLECTION_PROMPT.format(
            debug_example=DEBUG_REFLECTION_EXAMPLE,
            context=context,
            previous_impl=working_memory,
        )

        rsp = await self._aask(reflection_prompt, system_msgs=[REFLECTION_SYSTEM_MSG])
        print("???response:\n", rsp)

        return parse_reflection_impl_lenient(rsp)
        # reflection = json.loads(CodeParser.parse_code(block=None, lang="python", text=rsp))

        # return reflection
        # except:
        #     reflection = json.loads(rsp)

        # return reflection["improved_impl"]

    async def run(
        self,
        user_requirement: str,
        plan_status: str = "",
        tool_info: str = "",
        working_memory: list[Message] = None,
        use_reflection: bool = False,
        **kwargs,
    ) -> str:
        structual_prompt = STRUCTUAL_PROMPT.format(
            user_requirement=user_requirement,
            plan_status=plan_status,
            tool_info=tool_info,
        )

        working_memory = working_memory or []
        context = self.llm.format_msg([Message(content=structual_prompt, role="user")] + working_memory)

        # LLM call
        if use_reflection:
            code = await self._debug_with_reflection(context=context, working_memory=working_memory)
        else:
            rsp = await self.llm.aask(context, system_msgs=[INTERPRETER_SYSTEM_MSG], **kwargs)
            code = parse_python_code_lenient(rsp)

        return code


class CheckData(Action):
    async def run(self, plan: Plan) -> dict:
        finished_tasks = plan.get_finished_tasks()
        code_written = [remove_comments(task.code) for task in finished_tasks]
        code_written = "\n\n".join(code_written)
        prompt = CHECK_DATA_PROMPT.format(code_written=code_written)
        rsp = await self._aask(prompt)
        code = parse_python_code_lenient(rsp)
        return code
