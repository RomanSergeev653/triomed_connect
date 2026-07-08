from app.schemas import Appointment, FreeSlot


def _split_lines(value: str) -> list[str]:
    if not value or not value.strip():
        return []
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return [line.strip() for line in normalized.split("\n") if line.strip()]


def parse_free_slots(script_result: str) -> list[FreeSlot]:
    slots: list[FreeSlot] = []
    for line in _split_lines(script_result):
        parts = [part.strip() for part in line.split(";")]
        if len(parts) < 4:
            continue
        slots.append(
            FreeSlot(
                date=parts[0],
                doctor_id=parts[1],
                start_time=parts[2],
                end_time=parts[3],
            )
        )
    return slots


def parse_appointments(script_result: str) -> list[Appointment]:
    appointments: list[Appointment] = []
    for line in _split_lines(script_result):
        parts = [part.strip() for part in line.split(";")]
        if len(parts) < 6:
            continue
        appointments.append(
            Appointment(
                record_id=parts[0],
                date=parts[1],
                doctor_id=parts[2],
                start_time=parts[3],
                end_time=parts[4],
                interval=parts[5],
            )
        )
    return appointments
