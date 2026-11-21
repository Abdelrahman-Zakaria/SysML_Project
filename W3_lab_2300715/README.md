# Week 3:  SysML v2 Tool-Calling Agent

A bounded, deterministic tool-calling agent for querying, inspecting, and validating external **SysML v2** model elements (`BatteryPack`, `ThermalSensor`, `CoolingController`, `MaxOperatingTempReq`) with strict input validation, allowlisted local tool execution, typed SysML compilation, and offline fail-closed exit-gate tests.

---





## 1. Setup

From the repository root (`Week3_Lab_2300715`), create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Bash / Zsh:
# source .venv/bin/activate

pip install -r requirements.txt
```

---

## 2. Configure Environment Variables

Create a `.env` file in the repository root and add your Groq (or Hugging Face) credentials:

```env
PROVIDER=groq
MODEL_ID=openai/gpt-oss-120b
GROQ_API_KEY=your_groq_api_key_here
```



---

## 3. Run Offline Exit-Gate Tests

Runs the 6 offline `pytest` exit-gate tests (valid typed operations, fabricated tool names, invalid arguments, unsupported claims / missing elements, tool runtime failures & validator rejections, and call limits) without making live API calls:

```powershell
python -m pytest -v
```

---

## 4. Run the Live Agent

Starts the interactive CLI backed by `openai/gpt-oss-120b` via Groq:

```powershell
python agent.py
```


**Example Prompts:**
- `List all elements in the model and check if BatteryPack is ACTIVE.`
- `Add a Real attribute named nominalVoltage to BatteryPack.`
- `Add a Boolean constraint maxAllowedTempC >= 10.0 to MaxOperatingTempReq.`