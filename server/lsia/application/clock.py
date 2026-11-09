from sqlalchemy.orm import Session

from lsia.infrastructure.models import Meta

CLOCK_KEY = "lamport_clock"


def get_lamport(session: Session) -> int:
    row = session.get(Meta, CLOCK_KEY)
    if row is None:
        return 0
    return int(row.value)


def advance_lamport(session: Session, remote_clock: int = 0) -> int:
    row = session.get(Meta, CLOCK_KEY)
    if row is None:
        row = Meta(key=CLOCK_KEY, value="0")
        session.add(row)
        session.flush()
    current = int(row.value)
    current = max(current, remote_clock) + 1
    row.value = str(current)
    return current


def next_lamport(session: Session) -> int:
    return advance_lamport(session, 0)
