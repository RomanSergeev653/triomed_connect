from pydantic import BaseModel, Field, field_validator

# Домены прослойки — нельзя подставлять в host (иначе Connect бьёт сам в себя → 404)
_FORBIDDEN_MYDENTA_HOSTNAMES = frozenset(
    {
        "mydenta.limbrs.top",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
    }
)


class ConnectionCredentials(BaseModel):
    host: str = Field(
        ...,
        description=(
            "Адрес сервера MyDenta (IP:порт), например 178.124.210.218:443. "
            "Не указывайте домен Triomed Connect (mydenta.limbrs.top)."
        ),
    )
    database: str = Field(..., description="Название базы FileMaker")
    username: str
    password: str

    @field_validator("host")
    @classmethod
    def normalize_mydenta_host(cls, value: str) -> str:
        host = value.strip().removeprefix("https://").removeprefix("http://")
        host = host.split("/")[0].split("?")[0].rstrip("/")
        if not host:
            raise ValueError("host пустой")

        hostname = host.split(":")[0].lower()
        if (
            hostname in _FORBIDDEN_MYDENTA_HOSTNAMES
            or hostname.endswith(".limbrs.top")
        ):
            raise ValueError(
                "host должен быть адресом MyDenta (например 178.124.210.218:443), "
                "а не доменом Triomed Connect (mydenta.limbrs.top). "
                "Домен прослойки — только в URL запроса, не в поле host."
            )
        return host


class FreeSlotsRequest(ConnectionCredentials):
    date_start: str = Field(..., description="Дата начала, формат дд.мм.гггг")
    date_end: str = Field(..., description="Дата окончания, формат дд.мм.гггг")
    doctor_ids: list[str] | None = Field(
        default=None,
        description="ID врачей; если не указано — поиск по всем",
    )


class FreeSlot(BaseModel):
    date: str
    doctor_id: str
    start_time: str
    end_time: str


class FreeSlotsResponse(BaseModel):
    slots: list[FreeSlot]
    script_error: str
    raw: str | None = None


class DoctorsRequest(ConnectionCredentials):
    date_start: str = Field(..., description="Дата начала, формат дд.мм.гггг")
    date_end: str = Field(..., description="Дата окончания, формат дд.мм.гггг")


class Doctor(BaseModel):
    doctor_id: str
    full_name: str
    post_name: str


class DoctorsResponse(BaseModel):
    doctors: list[Doctor]
    status: str | None = None
    message: str | None = None
    script_error: str
    raw: str | None = None


class SearchAppointmentsRequest(ConnectionCredentials):
    phone: str = Field(..., description="Телефон с кодом страны без +, например 375291234567")
    last_name: str
    first_name: str
    middle_name: str = ""
    date: str | None = Field(default=None, description="Дата дд.мм.гггг, необязательно")


class Appointment(BaseModel):
    record_id: str
    date: str
    doctor_id: str
    start_time: str
    end_time: str
    interval: str


class SearchAppointmentsResponse(BaseModel):
    appointments: list[Appointment]
    script_error: str
    raw: str | None = None


class CreateAppointmentRequest(ConnectionCredentials):
    phone_local: str = Field(..., description="Телефон без кода страны")
    phone_code: str = Field(..., description="Код страны без +, например 375")
    last_name: str
    first_name: str
    middle_name: str = ""
    date: str
    start_time: str
    end_time: str
    doctor_id: str


class RescheduleAppointmentRequest(CreateAppointmentRequest):
    record_id: str
    comment: str


class ScriptResponse(BaseModel):
    script_result: str
    script_error: str
    raw: dict


class LogoutRequest(ConnectionCredentials):
    token: str | None = Field(
        default=None,
        description="Токен сессии; если не указан — используется кэшированный",
    )
