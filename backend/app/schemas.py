from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr



class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class OptimizationRunRequest(BaseModel):
    corridors: Optional[List[str]] = None  # corridor codes; None = all
    confidence_level: float = 0.95
    horizon_days: int = 7
    solver: str = "simulated_annealing"
    iterations: int = 8000
    initial_temperature: float = 1000.0
    cooling_rate: float = 0.995
    random_seed: Optional[int] = None
    onehot_penalty: Optional[float] = None
    weights: Optional[Dict[str, float]] = None
    demand_delta_pct: float = 0.0
    volatility_delta_pct: float = 0.0
    cutoff_delta_hours: float = 0.0
    run_type: str = "standard"
    scenario_name: Optional[str] = None
    global_liquidity_cap_musd: Optional[float] = None


class ScenarioRunRequest(BaseModel):
    corridors: Optional[List[str]] = None
    confidence_level: float = 0.95
    demand_delta_pct: float = 0.0
    volatility_delta_pct: float = 0.0
    cutoff_delta_hours: float = 0.0
    label: str = "Custom scenario"


class AgentAskRequest(BaseModel):
    session_id: Optional[str] = None
    question: str


class ApprovalRequest(BaseModel):
    run_id: int
    decision: str  # APPROVED | REJECTED | RECALCULATION_REQUESTED
    reason: Optional[str] = ""

class OptimizationConfigRequest(BaseModel):
    risk_appetite: str
    corridors: Optional[List[str]] = None
    iterations: Optional[int] = None
    initial_temperature: Optional[float] = None
    cooling_rate: Optional[float] = None

class SubmitApprovalRequest(BaseModel):
    submitted_by: str
    notes: Optional[str] = None
    confirmations: Optional[List[str]] = None

class ApprovalDecisionRequest(BaseModel):
    decision: str
    decided_by: str
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None
