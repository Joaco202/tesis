import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .repository import SupabaseRepository

class OfflineQueue:
    def __init__(self, repository: SupabaseRepository, base_dir: Path | None = None) -> None:
        self.repository = repository
        self.base_dir = base_dir or Path(__file__).resolve().parents[2] / "data" / "offline"
        self.queue_file = self.base_dir / "offline_queue.json"
        self.images_dir = self.base_dir / "images"
        
        self.images_dir.mkdir(parents=True, exist_ok=True)
        if not self.queue_file.exists():
            self.queue_file.write_text("[]", encoding="utf-8")

    def _read_queue(self) -> list[dict]:
        try:
            if self.queue_file.exists():
                return json.loads(self.queue_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Error reading offline queue JSON: {e}")
        return []

    def _write_queue(self, queue: list[dict]) -> None:
        try:
            self.queue_file.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"Error writing offline queue JSON: {e}")

    def add_event(self, *, patente: str, event_type: str, camera_id: str, confianza: float, timestamp: datetime, image_bytes: bytes | None = None) -> str | None:
        #Agrega un evento a la cola local y guarda la imagen en local.
        local_image_name = None
        if image_bytes is not None:
            ts_str = timestamp.strftime('%Y%m%d_%H%M%S')
            safe_plate = "".join([c for c in patente if c.isalnum()])
            local_image_name = f"{camera_id}_{ts_str}_{safe_plate}.jpg"
            local_image_path = self.images_dir / local_image_name
            try:
                local_image_path.write_bytes(image_bytes)
            except Exception as e:
                print(f"Error saving offline image file: {e}")
                local_image_name = None

        queue = self._read_queue()
        queue.append({
            "patente": patente,
            "event_type": event_type,
            "camera_id": camera_id,
            "confianza": confianza,
            "timestamp_utc": timestamp.isoformat(),
            "local_image_name": local_image_name
        })
        self._write_queue(queue)
        print(f"[COLA OFFLINE] Evento guardado localmente: {patente} ({event_type})")
        return local_image_name

    def sync_queue(self) -> int:
        """Intenta sincronizar los eventos guardados en la cola local con Supabase."""
        queue = self._read_queue()
        if not queue:
            return 0

        synced_count = 0
        remaining_queue = []

        print(f"[SYNC] Intentando sincronizar {len(queue)} eventos de la cola local...")

        for item in queue:
            success = False
            local_image_name = item.get("local_image_name")
            resolved_image_url = ""
            
            if local_image_name:
                local_image_path = self.images_dir / local_image_name
                if local_image_path.exists():
                    try:
                        self.repository.client.upload_file(
                            bucket="access-images",
                            remote_path=local_image_name,
                            file_path=local_image_path,
                            content_type="image/jpeg"
                        )
                        base_url_clean = self.repository.client.base_url.rstrip('/')
                        resolved_image_url = f"{base_url_clean}/storage/v1/object/public/access-images/{local_image_name}"
                        local_image_path.unlink()
                    except Exception as upload_err:
                        print(f"[SYNC] Error al subir imagen offline {local_image_name}: {upload_err}")
                        remaining_queue.append(item)
                        continue
            
            try:
                timestamp = datetime.fromisoformat(item["timestamp_utc"])
                self.repository.guardar_acceso(
                    patente=item["patente"],
                    event_type=item["event_type"],
                    camera_id=item["camera_id"],
                    confianza=item["confianza"],
                    image_origin=resolved_image_url,
                    timestamp_utc=timestamp
                )
                success = True
                synced_count += 1
                print(f"[SYNC] Sincronizado exitosamente: {item['patente']} ({item['event_type']})")
            except Exception as sync_err:
                print(f"[SYNC] Falló la persistencia de {item['patente']} en Supabase: {sync_err}")
                if not local_image_name or not (self.images_dir / local_image_name).exists():
                    item["local_image_name"] = None
                remaining_queue.append(item)

        self._write_queue(remaining_queue)
        return synced_count
