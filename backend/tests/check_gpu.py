import torch, time, numpy as np
from ultralytics import YOLO

device = "cuda"
model = YOLO("yolo26n.pt")
dummy = np.zeros((480, 640, 3), dtype=np.uint8)

print("Midiendo tiempos reales (10 inferencias en CUDA)...")
times = []
for i in range(12):
    t0 = time.perf_counter()
    model.predict(dummy, device=device, verbose=False)
    t1 = time.perf_counter()
    elapsed = t1 - t0
    times.append(elapsed)
    print(f"  Inferencia {i+1}: {elapsed*1000:.1f} ms")

#excluir primera (warmup) y segunda (primer warm) para promedio real
real_times = times[2:]
print(f"\nPromedio real (sin warmup): {sum(real_times)/len(real_times)*1000:.1f} ms")
print(f"Min: {min(real_times)*1000:.1f} ms | Max: {max(real_times)*1000:.1f} ms")
