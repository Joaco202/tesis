import cv2

def list_cameras():
    print("Buscando cámaras disponibles en el sistema (índices 0 al 9)...")
    available_cameras = []
    
    # Probar índices del 0 al 9
    for index in range(10):
        # Usar cv2.CAP_DSHOW en Windows para agilizar la detección
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            # Obtener resolución de la cámara para confirmar que funciona y dar información útil
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            print(f"[OK] Cámara detectada en el índice {index}: Resolución {int(width)}x{int(height)}")
            available_cameras.append(index)
            cap.release()
        else:
            # Probar sin CAP_DSHOW por si acaso
            cap_fallback = cv2.VideoCapture(index)
            if cap_fallback.isOpened():
                width = cap_fallback.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap_fallback.get(cv2.CAP_PROP_FRAME_HEIGHT)
                print(f"[OK] Cámara detectada en el índice {index} (Fallback): Resolución {int(width)}x{int(height)}")
                available_cameras.append(index)
                cap_fallback.release()
                
    if not available_cameras:
        print("\n[!] No se detectó ninguna cámara activa. Asegúrate de que el cable USB esté bien conectado y que los controladores estén instalados.")
    else:
        print(f"\n[Éxito] Cámaras disponibles: {available_cameras}")
        print("Para usar una cámara específica, ejecuta:")
        print(f"  ./start_system.ps1 -Source \"{available_cameras[0]}\"")

if __name__ == "__main__":
    list_cameras()
