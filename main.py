
import os

from dotenv import load_dotenv

from agent.agent import Agent
from agent.planner import RuleBasedPlanner, LLMPlanner


def main():

    load_dotenv()

    mode = os.getenv("AGENT_MODE", "demo")

    if mode == "llm":
        planner = LLMPlanner()
    else:
        planner = RuleBasedPlanner()

    agent = Agent(
        planner=planner,
        max_tool_calls=5
    )

    print("Safe SysML Agent")
    print("Type 'exit' to stop.\n")
    print("Active Planner:", type(planner).__name__)

    while True:

        user_request = input("You: ")

        if user_request.lower() == "exit":
            break

        result = agent.run(user_request)

        print("\nAgent Result:")
        print(result)
        print("-" * 50)


if __name__ == "__main__":
    main()
