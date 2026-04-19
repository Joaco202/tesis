from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .db import SupabaseClient


@dataclass(slots=True)
class AccessEventResult:
    plate_text: str
    event_type: str
    access_id: int | None
    status: str


class SupabaseRepository:
    def __init__(self, client: SupabaseClient, vehicles_table: str, accesses_table: str) -> None:
        self.client = client
        self.vehicles_table = vehicles_table
        self.accesses_table = accesses_table

    def guardar_vehiculo_si_no_existe(self, patente: str) -> None:
        self.client.insert(
            self.vehicles_table,
            [{"patente": patente}],
            on_conflict="patente",
            prefer="resolution=ignore-duplicates,return=minimal",
        )

    def registrar_entrada(
        self,
        *,
        patente: str,
        camera_id: str,
        confianza: float | None,
        image_origin: str,
        timestamp_utc: datetime,
    ) -> AccessEventResult:
        row = {
            "vehiculo_patente": patente,
            "camera_id": camera_id,
            "fecha_entrada": timestamp_utc.isoformat(),
            "confianza_ocr": confianza,
            "imagen_origen": image_origin,
        }
        created = self.client.insert(self.accesses_table, [row])
        access_id = created[0].get("id") if created else None
        return AccessEventResult(
            plate_text=patente,
            event_type="entrada",
            access_id=access_id,
            status="created",
        )

    def registrar_salida(
        self,
        *,
        patente: str,
        camera_id: str,
        confianza: float | None,
        image_origin: str,
        timestamp_utc: datetime,
    ) -> AccessEventResult:
        opened = self.client.select(
            self.accesses_table,
            query_params={
                "select": "id",
                "vehiculo_patente": f"eq.{patente}",
                "fecha_salida": "is.null",
                "order": "fecha_entrada.desc",
                "limit": "1",
            },
        )
        if not opened:
            return AccessEventResult(
                plate_text=patente,
                event_type="salida",
                access_id=None,
                status="skipped_no_open_access",
            )

        access_id = opened[0].get("id")
        if access_id is None:
            return AccessEventResult(
                plate_text=patente,
                event_type="salida",
                access_id=None,
                status="error_missing_access_id",
            )

        payload = {
            "fecha_salida": timestamp_utc.isoformat(),
            "camera_salida_id": camera_id,
            "confianza_ocr_salida": confianza,
            "imagen_origen_salida": image_origin,
        }
        self.client.update(self.accesses_table, payload, query_params={"id": f"eq.{access_id}"})
        return AccessEventResult(
            plate_text=patente,
            event_type="salida",
            access_id=access_id,
            status="updated",
        )

    def guardar_acceso(
        self,
        *,
        patente: str,
        event_type: str,
        camera_id: str,
        confianza: float | None,
        image_origin: str,
        timestamp_utc: datetime | None = None,
    ) -> AccessEventResult:
        normalized_type = event_type.strip().lower()
        timestamp = timestamp_utc or datetime.now(timezone.utc)
        self.guardar_vehiculo_si_no_existe(patente)

        if normalized_type == "entrada":
            return self.registrar_entrada(
                patente=patente,
                camera_id=camera_id,
                confianza=confianza,
                image_origin=image_origin,
                timestamp_utc=timestamp,
            )

        if normalized_type == "salida":
            return self.registrar_salida(
                patente=patente,
                camera_id=camera_id,
                confianza=confianza,
                image_origin=image_origin,
                timestamp_utc=timestamp,
            )

        return AccessEventResult(
            plate_text=patente,
            event_type=normalized_type,
            access_id=None,
            status="skipped_invalid_event_type",
        )
