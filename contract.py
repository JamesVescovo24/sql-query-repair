"""Typed SQL repair contract: a query is tested against several pinned datasets."""
from dataclasses import dataclass
from enum import Enum
from typing import Annotated
from slimconfig import Output

class Tool(Enum):
    PIN = "pin_sql_truth"
    READ = "read_sql_case"
    SAVE = "run_candidate_sql"

class Task(Enum):
    MAIN = "repair-sql"

@dataclass
class CaseInput(Output):
    case: Annotated[str, "Query case: region-revenue or overdue-count"]
    seed: Annotated[int, "Deterministic integer fixture seed, 1 through 10000"]

@dataclass
class Customer(Output):
    customer_id: int
    region: str

@dataclass
class Order(Output):
    order_id: int
    customer_id: int
    status: str
    due_date: str

@dataclass
class Payment(Output):
    payment_id: int
    order_id: int
    amount_cents: int

@dataclass
class Fixture(Output):
    label: str
    customers: list[Customer]
    orders: list[Order]
    payments: list[Payment]

@dataclass
class FixtureResult(Output):
    label: str
    columns: list[str]
    rows: Annotated[list[str], "Sorted JSON strings representing each row in column order; duplicates retained"]

@dataclass
class ReadOutput(Output):
    case: str
    seed: int
    schema: str
    requirement: str
    broken_query: str
    rules: str

@dataclass
class ReferenceOutput(Output):
    case: str
    seed: int
    fixtures: list[Fixture]
    expected: list[FixtureResult]

@dataclass
class RunInput(Output):
    case: str
    seed: int
    sql: Annotated[str, "Read-only SELECT statement that satisfies the requirement on every fixture"]

@dataclass
class RunOutput(Output):
    case: str
    seed: int
    sql: str
    path: str
    digest: str
    results: list[FixtureResult]

TOOLS = {Tool.PIN:(CaseInput,ReferenceOutput),Tool.READ:(CaseInput,ReadOutput),Tool.SAVE:(RunInput,RunOutput)}
TASKS = {Task.MAIN:(CaseInput,RunOutput)}
