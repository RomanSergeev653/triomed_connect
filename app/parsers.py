import json

from app.schemas import Appointment, Doctor, FreeSlot


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


def parse_doctors(script_result: str) -> tuple[list[Doctor], str | None, str | None]:
    """Parse get_list_doc JSON scriptResult → (doctors, status, message)."""
    if not script_result or not script_result.strip():
        return [], None, None

    try:
        payload = json.loads(script_result)
    except json.JSONDecodeError:
        return [], None, None

    if not isinstance(payload, dict):
        return [], None, None

    doctors: list[Doctor] = []
    for item in payload.get("list_doc") or []:
        if not isinstance(item, dict):
            continue
        doctor_id = item.get("id_doc")
        full_name = item.get("FullName")
        post_name = item.get("post_name")
        if doctor_id is None or full_name is None:
            continue
        doctors.append(
            Doctor(
                doctor_id=str(doctor_id),
                full_name=str(full_name),
                post_name=str(post_name) if post_name is not None else "",
            )
        )

    status = payload.get("status")
    message = payload.get("message")
    return (
        doctors,
        str(status) if status is not None else None,
        str(message) if message is not None else None,
    )
