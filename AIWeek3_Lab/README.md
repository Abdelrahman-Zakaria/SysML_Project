# AIWeek3 Lab

This lab builds a small, inspectable agent for SysML v2 model-element
inspection. The model proposes a named tool and typed arguments. Python
validates both, executes only allow-listed tools, and returns observable
evidence or an explicit failure. Model-generated prose is never accepted as
engineering evidence.

## Agent loop

1. Record the user request.
2. Give the model the available tools, descriptions, and JSON argument schemas.
3. Validate the proposed tool call and arguments.
4. Execute the matching deterministic tool or configured SysML validator.
5. Return evidence, rejection, missing evidence, timeout, or tool failure.

The default limits are three model/tool calls and 300 seconds total runtime.
This gives slow model endpoints and the local Java-based SysML kernel time to
respond and validate a proposal.
The remaining time is passed to the decision provider; the live provider uses
that value as the OpenAI-compatible client timeout. The configured validator also gets
only the remaining time. Provider exceptions and tool exceptions become
non-success results. Ctrl+C or EOF during input and Ctrl+C during a run are
reported as cancellation.

The result stores token data in `metadata.llm_token_usage`. The console presents
aggregate prompt, completion, and total counts plus model IDs and per-call
counts. The aggregate counts are summed across model calls. If the provider
omits usage metadata, the console says token counts were not reported; the lab
does not estimate them.

## Tools

The model may request only these four tools. Python checks each tool name and
its typed arguments before executing it.

| Tool | Arguments | Result |
| --- | --- | --- |
| `list_available_items` | `kind`: `all`, `package`, `part_definition`, `requirement_definition`, or `action_definition`; optional `limit` from 1 to 50 | IDs from the local example catalog, up to the limit |
| `get_metadata` | `item_id`: a known ID such as `ExampleRequirement` | The element's kind, SysML metaclass, description, documentation, and any example statement |
| `check_condition` | `item_id` and `condition`: `exists`, `has_documentation`, or `is_definition` | A true/false result computed from the local catalog |
| `propose_requirement` | `requirement_id` from `AIW3-001` to `AIW3-999`, and a one-line `statement` from 10 to 240 characters beginning `The system shall ` | A generated SysML v2 candidate, returned only after validation and marked for human review |

### Example requests

- “List all available model elements.” calls `list_available_items` with
  `kind=all`.
- “What kind of element is ExampleRequirement?” calls `get_metadata` with
  `item_id=ExampleRequirement`.
- “Does ExamplePackage have documentation?” calls `check_condition` with
  `condition=has_documentation`.
- “Propose a requirement that the system shall support a new operating mode.”
  asks the model to provide a new `AIW3-###` ID and the statement, then calls
  `propose_requirement`.

The first three tools use a small deterministic catalog of generic SysML v2
examples stored in `app.py`. This is teaching data: the lab does not load or
parse arbitrary model files. Requests for items outside the catalog return
`no_evidence` instead of allowing the model to invent facts.

`propose_requirement` builds a typed SysML candidate and sends its text
directly to the official OMG SysML v2 Pilot Implementation Jupyter kernel by
default. A successful validation returns `requires_review`; it does not edit a
project model. If validation fails, the tool returns an error and the proposal
is not reported as valid.

For example, a valid request could produce this candidate:

```sysml
package AIWeek3Candidate {
    requirement def <'AIW3-001'> ProposedRequirement {
        doc /* The system shall support a new operating mode. */
    }
}
```

The proposal ID must match `AIW3-###`. The statement cannot contain line breaks
or SysML comment delimiters. These checks keep the generated input within the
small typed operation this lab supports.

`SYSML_VALIDATOR=` should normally be left blank. The app then uses the
official `sysml` Jupyter kernel installed below. Set `SYSML_VALIDATOR` only to
override that default with a local wrapper. For that override path, the app
writes the candidate to a temporary `.sysml` file and passes its path as the
wrapper's only argument. The wrapper must return exit code 0 only when the
candidate passes validation. If the official kernel or custom wrapper cannot
run, the proposal fails closed.

The kernel is distributed by the [official SysML v2 Pilot Implementation
project](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation).

## Result statuses

- `success`: a deterministic tool returned evidence for the request.
- `no_evidence`: the requested ID is not in the local example catalog.
- `rejected`: the tool name or arguments were invalid, or the agent needs the
  request clarified.
- `tool_error`: the model provider or a tool failed, including a failed SysML
  validation.
- `limit_exceeded`: the call count or run-time limit was reached.
- `requires_review`: the SysML candidate passed validation and is waiting for a
  person to review it. The project model remains unchanged.
- `cancelled`: the user interrupted the run.

Each result also includes observations with the tool name and either evidence
or a specific error, plus the arguments that were attempted or validated. The
ordered `events` trace records the user message, each tool call and its
arguments, each tool result/error, and the final answer. The model history also
receives tool calls as assistant function-call messages and results as matching
tool messages. The trace records observable actions only; it does not store
hidden chain-of-thought. Token usage is printed separately in a readable
section; the structured values remain in `metadata.llm_token_usage` for
programmatic use.

## Setup

Week 3 has its own virtual environment and dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set the following values in `.env`:

| Variable | Purpose |
| --- | --- |
| `BASE_URL` | OpenAI-compatible chat endpoint URL for model decisions |
| `API_KEY` | Credential for that model endpoint |
| `MODEL_ID` | Model name or identifier accepted by the endpoint |
| `SYSML_VALIDATOR` | Optional custom validator wrapper. Leave blank to use the official kernel. |

The first three settings are needed for live model calls. Requirement
proposals require Java 21+ and the official SysML kernel. After installing the
Python requirements and activating the virtual environment, install the latest
official pilot kernel with:

```powershell
.\setup_official_sysml_kernel.ps1
```

The installer downloads the official kernel release and registers it with the
active Python environment. Keep `.env` and API keys out of version control. The
deterministic tests do not need a model API key or an installed SysML kernel.

```powershell
.\venv\Scripts\python.exe app.py
```

Example run (token counts vary by request and provider):

```text
=== SysML v2 Model Agent ===
I can help you:
- List generic SysML v2 model elements by kind.
- Inspect a package, part, requirement, or action definition.
- Check whether an element exists, has documentation, or is a definition.
- Propose a SysML requirement for official validation and human review.
Example: What kind of element is ExampleRequirement?
Proposals use the official kernel and are never applied automatically.

What should I inspect? What kind of element is ExampleRequirement?
=== Agent result ===
Status: SUCCESS
The result is supported by deterministic local evidence.

Tool: get_metadata
Arguments:
  Item id: ExampleRequirement
Evidence:
  Item id: ExampleRequirement
  Kind: requirement_definition
  Metaclass: RequirementDefinition
  Description: A requirement definition in a SysML v2 model.
  Statement: The system shall satisfy the example requirement.
  Documentation: Illustrates a requirement definition and its statement.

LLM token usage:
  Model: example-model
  Prompt: 85 | Completion: 13 | Total: 98 tokens
```

## Example runs

Run the command once for each example; the app handles one prompt per run. The
startup help appears before each prompt. The model's explanatory sentence and
token counts can vary, but tool names, evidence, and statuses should match the
examples. Requirement proposal examples need Java 21+ and the official SysML v2
kernel installed.

### List and filter model elements

```text
What should I inspect? List all available model elements.
=== Agent result ===
Status: SUCCESS
The result is supported by deterministic local evidence.

Tool: list_available_items
Arguments:
  Kind: all
  Limit: 20
Evidence:
  Items: ExamplePackage, ExamplePart, ExampleRequirement, ExampleAction
  Kind: all

LLM token usage:
  Model: <configured-model>
  Prompt: <provider count> | Completion: <provider count> | Total: <provider count> tokens
```

To filter the catalog, try `List the requirement definitions.` The tool should
return only `ExampleRequirement` with kind `requirement_definition`.

### Inspect metadata and check a condition

```text
What should I inspect? Does ExamplePackage have documentation?
=== Agent result ===
Status: SUCCESS
The result is supported by deterministic local evidence.

Tool: check_condition
Arguments:
  Item id: ExamplePackage
  Condition: has_documentation
Evidence:
  Item id: ExamplePackage
  Condition: has_documentation
  Value: Yes

LLM token usage:
  Model: <configured-model>
  Prompt: <provider count> | Completion: <provider count> | Total: <provider count> tokens
```

For metadata, enter `What kind of element is ExampleRequirement?`. The result
includes its `RequirementDefinition` metaclass, description, statement, and
documentation. Try `Inspect UnknownElement.` to see the `NO EVIDENCE` response;
the agent reports the missing catalog entry instead of making up metadata.

### Propose and validate a requirement

```text
What should I inspect? Propose a requirement that the system shall support a new operating mode.
=== Agent result ===
Status: REQUIRES REVIEW
The candidate passed validation and is awaiting human review; it was not applied.

Tool: propose_requirement
Arguments:
  Requirement id: AIW3-001
  Statement: The system shall support a new operating mode.
Evidence:
  Requirement id: AIW3-001
  Candidate sysml: package AIWeek3Candidate {
        requirement def <'AIW3-001'> ProposedRequirement {
            doc /* The system shall support a new operating mode. */
        }
    }
  Validator: OMG SysML v2 Pilot Implementation
  Validator result: passed
  Applied to model: No
  Human review: required

LLM token usage:
  Model: <configured-model>
  Prompt: <provider count> | Completion: <provider count> | Total: <provider count> tokens
```

If the kernel is unavailable or rejects the candidate, the result is
`TOOL ERROR`; it is never reported as validated. Invalid IDs (for example,
`AIW3-000`) and statements that do not start with `The system shall ` are
rejected before validation.

### Provider metadata and safe cancellation

For a live provider response with token metadata, each run ends with a readable
usage section like this (the provider supplies the values):

```text
LLM token usage:
  Model: <configured-model>
  Prompt: 85 | Completion: 13 | Total: 98 tokens
```

If the provider omits token metadata, the app prints `Token counts were not
reported by the provider.` Press `Ctrl+C` or send EOF at the prompt to cancel
input; press `Ctrl+C` during a run to get a `CANCELLED` result.

The automated tests use mocked model responses and validator calls, so they do
not need a live API key or an installed SysML kernel. Run them with:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

## Automated test coverage

The tests cover successful deterministic inspection, fabricated tool names,
invalid arguments, missing evidence, fabricated unsupported claims, malformed
model output, provider and tool exceptions, runtime and call limits, ambiguous
requests, cancellation, unavailable official kernel, validator rejection,
token-usage metadata aggregation, and a validated proposal awaiting human
review.
