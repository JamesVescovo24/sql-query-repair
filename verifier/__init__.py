"""NanoAgent verifier entrypoints (isolated, deterministic)."""
from contract import Task, Tool
from . import rules

TOOLS = {Tool.PIN: rules, Tool.READ: rules, Tool.SAVE: rules}
TASKS = {Task.MAIN: rules.verify_task}

def verify_input(tool, value):
    return rules.verify_input(Tool(tool), value)

def verify_output(tool, input_value, output_value, workspace):
    return rules.verify_output(Tool(tool), input_value, output_value, workspace)

def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
