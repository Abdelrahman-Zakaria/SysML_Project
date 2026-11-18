
PROMPT_VERSION = "1.0"

def build_intent_prompt(user_description: str) -> str:
    return f"""
You are a System Requirements Analyst.

Your task is to extract structured information
from a natural-language description of an engineering system.

USER DESCRIPTION:
{user_description}

Extract the following information:

1. schema_version:
   Always use "1.0".

2. system_name:
   A concise name for the system.

3. system_type:
   Choose exactly one of:
   - charging_system
   - powertrain
   - motor_controller
   - thermal_management
   - vehicle_control_unit
   - other

4. description:
   A short summary of the system.

5. components:
   A list of the main components explicitly mentioned
   or clearly identified in the description.

6. requirements:
   Extract all functional and performance requirements.

   Each requirement must be a JSON object containing:

   - type: Either "functional" or "performance".
   - description: A concise description of the requirement.

   Classification rules:
   - Functional: Describes what the system must do.
   - Performance: Describes measurable system performance,
     such as capacity, speed, accuracy, or efficiency.

7. constraints:
   Identify explicit limitations imposed on the system,
   such as operating conditions, budget, size, or technology restrictions.

IMPORTANT:
- Extract information only from the user description.
- Do not invent technical specifications.
- Do not assume missing values.
- Keep requirements clear and concise.
- Every requirement must have exactly two fields:
  "type" and "description".
- Do not classify performance requirements as constraints.
- A requirement containing a number is not automatically a constraint.
- Do not invent constraints.
- If no explicit constraints exist, return an empty list.
- Return valid JSON only.
- Do not use Markdown code fences.
- Do not include explanations outside the JSON.

OUTPUT FORMAT:
Return a valid JSON object containing exactly these fields:

schema_version, system_name, system_type,
description, components, requirements, constraints.
"""
