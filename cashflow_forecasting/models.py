@dataclass
class Transaction:
    date: datetime
    amount: float
    description: str

@dataclass
class ForecastResult:
    date: datetime
    predicted_balance: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None

@dataclass
class Alert:
    date: datetime
    message: str
    severity: str  # "low", "medium", "high"
