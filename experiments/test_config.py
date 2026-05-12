from metagpt.config2 import Config
from metagpt.roles import Role
from role import SciDataInterpreter
from metagpt.schema import Message, MessageQueue, SerializationMixin
from metagpt.context_mixin import ContextMixin
from pydantic import BaseModel
from metagpt.actions.di.write_plan import WritePlan

# Example configurations for gpt-4, gpt-4-turbo and gpt-3.5-turbo
gpt35 = Config.from_sab_config("test_config.yaml")  # Load custom configuration from `~/.metagpt` directory `gpt-4.yaml`
# print(gpt35)
A = SciDataInterpreter(config=gpt35)
# A.actions[0].set_config(Config.from_home("test_config.yaml"), override=False)
# A.actions[0].llm.config = Config.from_home("test_config.yaml")
# A.planner.set_plan_writter(Config.from_home("test_config.yaml"))
# print(A.planner.plan_writter.llm.config)
print(WritePlan().llm)
# print(SciDataInterpreter.__mro__)
from inspect import signature

# Check the __init__() signature of the relevant classes
# print(signature(Role.__init__))
# print(signature(SerializationMixin.__init__))
# print(signature(ContextMixin.__init__))
# print(signature(BaseModel.__init__))

