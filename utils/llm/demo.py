from utils.llm.dspy_inference import DSPYInference
import dspy
import asyncio
import os
import subprocess
from pathlib import Path
import sys

if len(sys.argv) < 2:
    print("Error: Please provide a repository path as the first argument. Example: python demo.py /home/*username*/git/*forge-project-name*/")
    sys.exit(1)
    
repo_dir = Path(sys.argv[1])

approved_commands = [
    'forge',
    'npm',
    'solc',
    'foundryup',
    'pnpm',
    'yarn',
    'git submodule',
    'nvm'
]


def list_files_tool(relative_path: str | None = None) -> list[str] | str:
    """List all files in the given relative path."""

    if relative_path is None:
        relative_path = '.'

    if '..' in relative_path:
        print("LLM tried to access parent directory! Returning empty list.")
        return 'Restricted: Tried to access parent directory!'

    absolute_path = repo_dir / relative_path

    if not os.path.exists(absolute_path):
        print(f"Directory {relative_path} does not exist! Returning empty list.")
        return 'Error: Directory {relative_path} does not exist!'

    print("Listing files in: " + relative_path)
    return [f for f in os.listdir(absolute_path) if os.path.isfile(os.path.join(absolute_path, f))]

def list_folders_tool(relative_path: str | None = None) -> list[str] | str:
    """List all folders in the given relative path."""

    if relative_path is None:
        relative_path = '.'

    if '..' in relative_path:
        print("LLM tried to access parent directory! Returning empty list.")
        return 'Restricted: Tried to access parent directory!'

    absolute_path = repo_dir / relative_path

    if not os.path.exists(absolute_path):
        print(f"Directory {relative_path} does not exist! Returning empty list.")
        return 'Error: Directory {relative_path} does not exist!'

    print("Listing folders in: " + relative_path)
    return [f for f in os.listdir(absolute_path) if os.path.isdir(os.path.join(absolute_path, f))]

def read_file_tool(relative_path: str) -> str:
    """Read the contents of the given file."""

    if '..' in relative_path:
        print("LLM tried to access parent directory!")
        return 'Restricted: Tried to access parent directory!'
    
    absolute_path = repo_dir / relative_path

    if not os.path.exists(absolute_path):
        print(f"File {relative_path} does not exist!")
        return 'Error: File {relative_path} does not exist!'
    
    with open(absolute_path, 'r') as file:
        print("File read successfully: " + relative_path)
        return file.read()
    
def execute_command_tool(command: str, relative_path: str = '.', accept_nonzero_return_code: bool = False) -> tuple[str, int]:
    """Execute the given command inside of the given relative path and whether a non-zero return code is acceptable. Returns the output with "done" appended if the command was successful and the return code."""

    print(f"Attempting to execute command: {command} in {relative_path}")
    if not any(command.startswith(cmd) for cmd in approved_commands):
        print("Command must start with one of the following: " + ', '.join(approved_commands) + "!")
        return 'Error: Command must start with one of the following: ' + ', '.join(approved_commands), 1
    
    if '..' in relative_path:
        print("LLM tried to access parent directory!")
        return 'Restricted: Tried to access parent directory!', 1
    
    absolute_path = repo_dir / relative_path

    if not os.path.exists(absolute_path):
        print(f"Directory {relative_path} does not exist!")
        return 'Error: Directory {relative_path} does not exist!', 1

    try:
        result = subprocess.run(command, shell=True, cwd=absolute_path, capture_output=True, text=True)
        print("Command executed: " + command)
        if not accept_nonzero_return_code and result.returncode != 0:
            return 'Error: ' + result.stderr + '\nOutput: ' + result.stdout, result.returncode
        return 'Output: ' + result.stdout + '\ndone', result.returncode
    except subprocess.CalledProcessError as e:
        return 'Error: ' + str(e), 1
    
def prompt_modify_file_tool(relative_path: str, new_content: str, oneline_modification_reason: str) -> str:
    """Overwrite an existing file with the given new content. The file will be modified in place."""

    if '..' in relative_path:
        print("LLM tried to access parent directory! Returning empty string.")
        return 'Restricted: Tried to access parent directory!'
    
    absolute_path = repo_dir / relative_path
    
    if not os.path.exists(absolute_path):
        print(f"File {relative_path} does not exist! Returning empty string.")
        return f'Error: File {relative_path} does not exist!'
    
    print(f"LLM wants to modify file {relative_path}")
    print(f"Reason: {oneline_modification_reason}")
    print("Do you want to continue? (y/n)")
    response = input().lower()
    if response != 'y':
        print("Modification cancelled by user.")
        return 'Failure: Modification cancelled by user!'
    
    with open(absolute_path, 'w') as file:
        file.write(new_content)
        
    return 'Success: File modified!'

def final_check_before_completion() -> str:
    """Always run this tool before finishing. This tool will tell you whether you are done or not."""

    print('Trying to finish up...')

    result1, returncode1 = execute_command_tool('forge build')
    if returncode1 != 0:
        return 'Failure: Forge build failed! Please continue getting the repo to build. Here is your output: ' + result1
    
    print('Forge build passed! Trying to run tests...')

    result2, returncode2 = execute_command_tool('forge test', accept_nonzero_return_code=True)

    if result2.startswith('Error:') or result2.startswith('Failure:') or result2.startswith('Restricted:'):
        return 'Failure: Forge test failed! Please continue getting the repo tests to run. Here is your output: ' + result2
    
    print('Forge test passed! Should exit now...')
    
    return 'Success: Forge build and test passed!'

class RunCommands(dspy.Signature):
    """Run commands in the given directory."""

    high_level_instructions: str = dspy.InputField()
    forge_build_runs: bool = dspy.OutputField()
    forge_test_runs: bool = dspy.OutputField()
    ran_commands: list[str] = dspy.OutputField()


subprocess.run(['git', 'reset', '--hard'], cwd=repo_dir)
subprocess.run(['git', 'clean', '-fdx'], cwd=repo_dir)

inf_module = DSPYInference(
    pred_signature=RunCommands(),
    tools=[list_files_tool, list_folders_tool, read_file_tool, execute_command_tool, prompt_modify_file_tool, final_check_before_completion],
    max_iters=20,
)

result = asyncio.run(inf_module.run(
    high_level_instructions=f"""
        You are a professional smart contract security engineer.
        Your current directory is inside of a git repository of a Foundry Forge Solidity project.
        Your job is to build the project and run the tests.
        You are allowed to read through files and folders in the project to understand it.
        You can additionally only run the following commands at the root of the project:
        {', '.join(approved_commands)}
        You will not combine commands with && or ||.
        You will always try to use the non-interactive or json versions of the commands.
        You are allowed to use the help parameter of the commands if you want to understand them better.
        When supplying any relative path to a tool you will never use `..`. This is forbidden and will cause the tool to fail.
        You are not allowed to move freely using `cd`.
        You can additionally modify any file in the project that you have already read.
        Your goal is to run `forge build` successfully and to run `forge test` (which must complete but may have failing tests).
        You will not give up until these commands run successfully.
        You will never run any commands that open ports or a shell.
        You only have one shot at this so make sure to do it right.
        You should start by finding and opening the readme. Then, you should see what other files and folders are in the project.
        Your response will always finish with a call to `final_check_before_completion` that returns a success.
    """
))

print(result.ran_commands)
