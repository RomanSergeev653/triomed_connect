from fastapi import APIRouter

from app.mydenta_client import MyDentaClient
from app.parsers import parse_appointments, parse_doctors, parse_free_slots
from app.schemas import (
    CreateAppointmentRequest,
    DoctorsRequest,
    DoctorsResponse,
    FreeSlotsRequest,
    FreeSlotsResponse,
    LogoutRequest,
    RescheduleAppointmentRequest,
    ScriptResponse,
    SearchAppointmentsRequest,
    SearchAppointmentsResponse,
)

router = APIRouter(prefix="/api/v1")


def _join_script_param(values: list[str]) -> str:
    return "|".join(values)


@router.post("/free-slots", response_model=FreeSlotsResponse)
async def find_free_slots(body: FreeSlotsRequest) -> FreeSlotsResponse:
    client = MyDentaClient(body)
    params = [body.date_start, body.date_end]
    if body.doctor_ids:
        params.append("_".join(body.doctor_ids))

    result = await client.run_script("find_free_time", _join_script_param(params))
    script_result = result["script_result"]

    return FreeSlotsResponse(
        slots=parse_free_slots(script_result),
        script_error=result["script_error"],
        raw=script_result or None,
    )


@router.post("/doctors", response_model=DoctorsResponse)
async def find_doctors(body: DoctorsRequest) -> DoctorsResponse:
    client = MyDentaClient(body)
    result = await client.run_script(
        "get_list_doc",
        _join_script_param([body.date_start, body.date_end]),
    )
    script_result = result["script_result"]
    doctors, status, message = parse_doctors(script_result)

    return DoctorsResponse(
        doctors=doctors,
        status=status,
        message=message,
        script_error=result["script_error"],
        raw=script_result or None,
    )


@router.post("/appointments/search", response_model=SearchAppointmentsResponse)
async def search_appointments(body: SearchAppointmentsRequest) -> SearchAppointmentsResponse:
    client = MyDentaClient(body)
    params = [body.phone, body.last_name, body.first_name, body.middle_name]
    if body.date:
        params.append(body.date)

    result = await client.run_script("find_record_shedule", _join_script_param(params))
    script_result = result["script_result"]

    return SearchAppointmentsResponse(
        appointments=parse_appointments(script_result),
        script_error=result["script_error"],
        raw=script_result or None,
    )


@router.post("/appointments", response_model=ScriptResponse)
async def create_appointment(body: CreateAppointmentRequest) -> ScriptResponse:
    client = MyDentaClient(body)
    script_param = _join_script_param(
        [
            body.phone_local,
            body.phone_code,
            body.last_name,
            body.first_name,
            body.middle_name,
            body.date,
            body.start_time,
            body.end_time,
            body.doctor_id,
        ]
    )
    result = await client.run_script("create_record_shedule_api", script_param)
    return ScriptResponse(**result)


@router.post("/appointments/reschedule", response_model=ScriptResponse)
async def reschedule_appointment(body: RescheduleAppointmentRequest) -> ScriptResponse:
    client = MyDentaClient(body)
    script_param = _join_script_param(
        [
            body.phone_local,
            body.phone_code,
            body.last_name,
            body.first_name,
            body.middle_name,
            body.date,
            body.start_time,
            body.end_time,
            body.doctor_id,
            body.record_id,
            body.comment,
        ]
    )
    result = await client.run_script("create_record_shedule_api", script_param)
    return ScriptResponse(**result)


@router.post("/sessions/logout")
async def logout(body: LogoutRequest) -> dict:
    client = MyDentaClient(body)
    return await client.logout(body.token)
