"""Task-scoped, opt-in simulator requests. A decision is never proof of a stop."""

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class Task:
    task_id: str
    actions: frozenset[str]
    objects: frozenset[str] = frozenset()
    bounds_xy: tuple[float, float, float, float] = (-.86, .86, -.58, .58)
    edge_margin_m: float = .12

    def __post_init__(self):
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise ValueError("A task must have an identity")
        if len(self.bounds_xy) != 4 or not all(math.isfinite(v) for v in self.bounds_xy):
            raise ValueError("Table bounds must be finite")
        x0, x1, y0, y1 = self.bounds_xy
        if x1 <= x0 or y1 <= y0 or not 0 < self.edge_margin_m < min(x1-x0,y1-y0)/2:
            raise ValueError("Table bounds and edge margin are inconsistent")


@dataclass(frozen=True)
class Request:
    request_id: str
    task_id: str
    action: str
    object_id: str | None = None
    target_xy: tuple[float, float] | None = None


@dataclass(frozen=True)
class Decision:
    request_id: str
    task_id: str
    action: str
    status: str
    reason: str
    send_to_controller: bool = False
    physical_stop_confirmed: bool = False

    def to_dict(self):
        return asdict(self)


class TaskGate:
    """Allowlisted skills, object scope and measured full-body tabletop margin.

    Movement paths and manipulation need validated skills, not just endpoint
    checks. Unimplemented skills are refused even with task permission.
    """

    def __init__(self, task: Task, *, controls_enabled=False):
        if type(controls_enabled) is not bool:
            raise ValueError("Simulator controls require an explicit boolean")
        self.task = task
        self.controls_enabled = controls_enabled
        self._seen = set()

    def decide(self, request: Request, observation: dict, *, now_s: float) -> Decision:
        def result(status, reason, send=False):
            return Decision(request.request_id, request.task_id, request.action, status, reason, send)
        if not isinstance(request.request_id, str) or not request.request_id.strip() or len(request.request_id) > 128:
            return result("denied", "A request identity is required")
        if not isinstance(request.task_id, str) or not isinstance(request.action, str) or (
                request.object_id is not None and not isinstance(request.object_id, str)):
            return result("denied", "Task, action and object identities must be text")
        if len(self._seen) >= 10000:
            return result("denied", "Start a new task session before more requests")
        if request.request_id in self._seen:
            return result("denied", "This request has already been handled")
        self._seen.add(request.request_id)
        if request.task_id != self.task.task_id:
            return result("denied", "This request belongs to a different task")
        if request.action not in self.task.actions:
            return result("denied", "This action is outside the task you allowed")
        if request.object_id is not None and request.object_id not in self.task.objects:
            return result("denied", "This object is outside the task you allowed")
        try:
            stamp = observation["time_s"]
            margin = observation["table_margin_m"]
            if any(isinstance(v, bool) or not isinstance(v, (float, int)) for v in (stamp, margin, now_s)):
                raise ValueError
            if not all(math.isfinite(v) for v in (stamp, margin, now_s)):
                raise ValueError
            if observation.get("finite") is not True or not 0 <= now_s - stamp < .15:
                raise ValueError
        except (KeyError, TypeError, ValueError, OverflowError):
            return result("unknown", "Fresh measured robot state is unavailable")
        if margin < self.task.edge_margin_m:
            return result("denied", "The robot needs more clearance from the table edge")
        if request.target_xy is not None:
            try:
                x, y = request.target_xy
                x0, x1, y0, y1 = self.task.bounds_xy
                # Conservative destination inset, including body reach. This
                # alone does not validate any movement path.
                inset = self.task.edge_margin_m + .30
                if not (math.isfinite(x) and math.isfinite(y) and
                        x0 + inset <= x <= x1 - inset and y0 + inset <= y <= y1 - inset):
                    return result("denied", "That destination is too close to the table edge")
            except (TypeError, ValueError):
                return result("denied", "A destination must contain two finite coordinates")
        if request.action not in {"wave", "bow", "paw", "salute"}:
            return result("unavailable", "This task needs a validated movement or manipulation skill")
        if not self.controls_enabled:
            return result("observed", "Observation only. Simulator controls are disabled")
        return result("allowed", "Within the task and current tabletop clearance", True)
