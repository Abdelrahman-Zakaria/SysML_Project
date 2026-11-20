# Agent Fundamentals and Safe Tool Calling

## 1. Project Overview

This project is a Python-based AI agent that interacts with a simulated Elevator System through a predefined set of local tools.

The application receives a natural-language request, sends it to an AI model, and allows the model to select and request the execution of available tools.

Before execution, the requested tool and its arguments are validated locally. The corresponding Python function then executes and returns information from the Elevator System data.

The agent can inspect system elements, retrieve their metadata, and check specific conditions.

**The objective is to understand agent fundamentals, implement controlled tool calling, and ensure that tool execution is validated and restricted rather than allowing unrestricted model-generated actions.**

**Important:** The current Elevator System is represented by a local Python dictionary. Integration with an actual SysML model or SysML compiler is not implemented in this lab.

## 2. Technologies Used

- Python
- NVIDIA NIM API
- OpenAI Python SDK
- Pydantic
- Pytest
- JSON
- Python-dotenv

## 3. Project Architecture

The application follows an agent execution loop:

1. **User Request:** Receive a natural-language request about the Elevator System.
2. **AI Inference:** Send the request and available tool definitions to the AI model.
3. **Tool Selection:** The model decides whether a tool is needed and selects an available function.
4. **Argument Extraction:** Extract the requested tool name and its JSON arguments.
5. **Tool Validation:** Check the tool name against the predefined tool registry and validate its arguments using Pydantic.
6. **Tool Execution:** Execute the corresponding local Python function only after successful validation.
7. **Tool Observation:** Return the execution result to the model.
8. **Final Response:** The model uses the available tool results to answer the user.
9. **Execution Control:** Enforce a maximum of five tool calls per agent execution.

**Main execution principle:**

**The LLM proposes and selects actions → Python validates and controls execution → Tools return the actual available data.**

The model does not directly execute Python code or access arbitrary functions.

### Main Components

| File | Responsibility |
|---|---|
| `config.py` | Loads API credentials and model configuration from environment variables. |
| `schemas.py` | Defines Pydantic input schemas for tool argument validation. |
| `tools.py` | Implements deterministic functions that interact with the local Elevator System data. |
| `agent.py` | Maintains the tool registry, validates tool requests, and executes approved functions. |
| `main.py` | Defines the AI tools, communicates with NVIDIA, manages the agent loop, and handles user interaction. |

## 4. Project Structure

```text
LAB_3/
│
├── src/
│   ├── main.py
│   ├── tools.py
│   ├── schemas.py
│   ├── agent.py
│   └── config.py
│
├── tests/
│   ├── test_tools.py
│   └── test_agent.py
│
├── .gitignore
├── requirements.txt
└── README.md
```

The `.env` file and `.venv/` directory are local environment resources and are excluded from Git.

## 5. Elevator System and Available Tools

The agent operates on a simulated Elevator System containing five elements.

| ID | Name | Type | Status |
|---|---|---|---|
| 1 | Elevator | Part | Available |
| 2 | Motor | Part | Available |
| 3 | Door | Part | Available |
| 4 | OverloadProtection | Requirement | Defined |
| 5 | LoadLimit | Constraint | Defined |

### Available Tools

The application provides three predefined tools:

| Tool | Input | Description |
|---|---|---|
| `list_available_items` | No arguments | Returns the available Elevator System elements. |
| `get_metadata` | `item_id` | Retrieves the metadata of a specific element. |
| `check_condition` | `item_id`, `condition` | Checks whether an element satisfies a requested condition. |

The supported conditions are:

- `exists`
- `available`
- `defined`

These functions operate independently of the AI model. The model selects the appropriate function, while the Python implementation retrieves and evaluates the actual data.

## 6. Tool Validation and Execution

The project uses Pydantic to validate tool arguments before executing functions.

### Input Validation

The defined schemas enforce the following restrictions:

- `extra="forbid"` rejects unexpected arguments.
- `Field(gt=0)` ensures that item IDs are positive.
- `Literal` restricts condition values to the supported options.
- Required fields must be provided.

### Tool Registry

The application uses a predefined `TOOL_REGISTRY` that maps each permitted tool name to its Python function and corresponding Pydantic schema.

This prevents the model from executing arbitrary functions.

### Error Handling

The execution layer handles:

- Unknown tool names.
- Invalid or missing arguments.
- Unexpected additional arguments.
- Tool execution failures.
- Invalid JSON arguments.
- Non-object tool arguments.

Invalid requests return structured error information instead of being silently executed.

## 7. Installation and Setup

### Prerequisites

- Python 3.10 or later.
- An NVIDIA API key.
- Internet connection.

### Create a Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

## 8. Environment Configuration

The application uses environment variables to protect API credentials and configure the selected model.

Configure the following variables in PowerShell:

```powershell
$env:NVIDIA_API_KEY="your_actual_nvidia_api_key"
$env:MODEL="nvidia/nemotron-3.5-super-vl-120b-a12b"
```

The application communicates with NVIDIA through its OpenAI-compatible API endpoint.

These variables are available only in the current PowerShell session unless configured permanently.

Each developer must provide their own API key.

**Never hardcode API keys in source files or upload them to GitHub.**

## 9. Running the Application

From the project root, execute:

```powershell
python -m src.main
```

The application starts an interactive command-line session.

Example requests:

**List system elements:**

```text
List all elevator system elements.
```

**Retrieve metadata:**

```text
Give me the metadata of item 2.
```

**Check a condition:**

```text
Is the motor available?
```

**Check a defined requirement:**

```text
Is overload protection available?
```

The agent selects the appropriate tool, executes it after validation, and uses the returned information to generate its response.

To terminate the application, enter:

```text
exit
```

or:

```text
quit
```

## 10. Agent Execution Control and Safety

The application implements several controls to restrict tool execution.

| Control | Implementation |
|---|---|
| Tool allowlisting | Only functions registered in `TOOL_REGISTRY` can execute. |
| Argument validation | Pydantic validates arguments before execution. |
| Extra argument rejection | Unexpected fields are rejected. |
| Tool error handling | Execution errors are returned instead of being treated as successful results. |
| Invalid JSON handling | Malformed arguments are rejected. |
| Maximum tool calls | A maximum of five tool calls is allowed per agent execution. |
| API timeout | The API client uses a 30-second timeout. |
| Evidence-based responses | The system prompt instructs the model not to invent tool results and to acknowledge insufficient information. |

**Important distinction:** Prompt instructions encourage evidence-based responses, but they do not constitute a formal guarantee against hallucinations. Reliable engineering verification requires an authoritative validation mechanism.

## 11. Automated Testing

The project uses Pytest to verify tool execution, argument validation, error handling, and agent execution limits.

Run all tests:

```powershell
python -m pytest -v
```

### Current Test Coverage

**Tool and validation tests (`test_tools.py`):**

- Listing all Elevator System elements.
- Retrieving valid element metadata.
- Handling nonexistent element IDs.
- Checking available conditions.
- Checking defined conditions.
- Rejecting unsupported conditions.
- Rejecting unknown tool names.
- Rejecting invalid arguments.
- Rejecting unexpected additional arguments.
- Handling tool execution failures.
- Handling requests for nonexistent information.

**Agent execution tests (`test_agent.py`):**

- Verifying the maximum tool-call limit.
- Ensuring execution stops after five tool calls.

The agent execution test uses mocks to simulate API responses and tool execution. It does not require actual NVIDIA inference calls.

**The current test suite contains 12 tests, all of which pass.**

## 12. Future Integration with SysML

The current implementation demonstrates the fundamentals of a controlled AI agent using a simulated Elevator System.

The same architecture can be extended to interact with actual SysML models.

A possible future integration would include:

1. **Model Inspection:** Retrieve elements, relationships, and requirements from an actual SysML model.
2. **Typed Operation Proposals:** Allow the agent to propose structured operations using predefined schemas.
3. **Operation Validation:** Validate proposed operations against the model's structure and rules.
4. **Authoritative Verification:** Use a SysML compiler or official validator to verify engineering correctness.
5. **Controlled Execution:** Execute approved operations only after validation.

The intended architecture is:

**LLM proposes an operation → Python validates the request → SysML validation confirms correctness → Approved operation is executed.**

This future integration would connect the agent fundamentals studied in this lab with the broader graduation project objective.

**Actual SysML model integration, operation execution, and compiler-based validation are outside the scope of the current lab.**