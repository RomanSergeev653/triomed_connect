from pydantic import BaseModel, Field


class ConnectionCredentials(BaseModel):
    host: str = Field(..., description="Адрес сервера MyDenta, например 192.168.1.10:8080")
    database: str = Field(..., description="Название базы FileMaker")
    username: str
    password: str


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
