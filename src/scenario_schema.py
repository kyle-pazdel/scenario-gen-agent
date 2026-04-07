from typing import List, Literal
from pydantic import BaseModel, Field

class RedTeam(BaseModel):
    objective: str = Field(description="The main goal of the red team (attacker) in this scenario.")
    mitre_tactics: List[str] = Field(description="List of MITRE ATT&CK tactic IDs relevant to the attack.")
    steps: List[str] = Field(description="Ordered steps the red team takes to achieve their objective.")
    tools: List[str] = Field(description="Tools used by the red team during the attack.")

class BlueTeam(BaseModel):
    objective: str = Field(description="The main goal of the blue team (defender) in this scenario.")
    steps: List[str] = Field(description="Ordered steps the blue team takes to detect and respond to the attack.")
    tools: List[str] = Field(description="Tools used by the blue team during detection and response.")

class Environment(BaseModel):
    os: str = Field(description="Operating system(s) present in the scenario environment.")
    network_topology: str = Field(description="Description of the network topology for the scenario.")
    services: List[str] = Field(description="List of key services running in the environment.")

class ScenarioSpec(BaseModel):
    title: str = Field(description="Short, descriptive scenario title.")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(description="Scenario difficulty level: beginner, intermediate, or advanced.")
    red_team: RedTeam = Field(description="Red team (attacker) details for the scenario.")
    blue_team: BlueTeam = Field(description="Blue team (defender) details for the scenario.")
    environment: Environment = Field(description="Technical environment in which the scenario takes place.")
    learning_objectives: List[str] = Field(description="List of learning objectives for the scenario.")
    estimated_duration_minutes: int = Field(description="Estimated time to complete the scenario, in minutes.")
