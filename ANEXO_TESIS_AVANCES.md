# Anexo: Implementación, Optimizaciones y Referencias del Pipeline de Visión + OCR

Este documento contiene la redacción académica y las referencias bibliográficas estructuradas bajo la norma **IEEE** correspondientes a los últimos desarrollos y optimizaciones aplicados al **Sistema de Apoyo a la Gestión del Estacionamiento en Campus Fernando May**. Puedes copiar y pegar estas secciones directamente en tu documento de tesis (Word, LaTeX u Overleaf).

---

## 1. Redacción Académica para la Tesis

### 1.1 Optimización del Reconocimiento de Caracteres (OCR) mediante Benchmark A/B
Para mejorar la tasa de acierto y la latencia del reconocimiento óptico de caracteres (OCR) sobre los recortes de placas patentes localizadas por la red neuronal YOLOv8n, se llevó a cabo un estudio experimental comparativo (Benchmark A/B) utilizando un lote de pruebas con **90 imágenes reales** capturadas en el estacionamiento del Aula Magna del Campus Fernando May.

El análisis comparó dos enfoques de procesamiento dentro del motor de inteligencia artificial **PaddleOCR 3.5.0**:
* **Método A (Línea Base Legacy):** Pipeline completo que incluye preprocesadores de análisis de documentos de PaddleX (módulos de des-ondulación tridimensional `UVDoc`, clasificación de orientación del documento `doc_ori` y orientación de líneas de texto `textline_ori`).
* **Método B (Optimizado):** Pipeline optimizado con la desactivación explícita de dichos preprocesadores de documentos, pasando directamente la imagen recortada y escalada al reconocedor de caracteres.

La justificación teórica de esta optimización radica en que los preprocesadores de PaddleX están diseñados para digitalizar documentos escaneados de gran escala (libros arrugados, facturas rotadas). Al ser aplicados sobre regiones de interés (ROI) pequeñas y pre-alineadas (como el recorte de una patente vehicular de 150 píxeles), el algoritmo de des-ondulación distorsionaba geométricamente los bordes de los caracteres legibles, induciendo a errores de segmentación.

Los resultados del benchmark experimental se resumen en la Tabla 1.1:

| Métrica Evaluada | Método A (Con Preprocesadores) | Método B (Optimizado) | Variación (%) |
| :--- | :---: | :---: | :---: |
| **Patentes Detectadas Correctamente** | 27 / 90 | **44 / 90** | **+62.96%** |
| **Confianza Promedio del OCR** | 90.4% | 89.9% | -0.5% (Insignificante) |
| **Tiempo de Inferencia Promedio (s)** | 1.27 s | **0.39 s** | **-69.29% (3.3x más rápido)** |

*Tabla 1.1: Resultados del Benchmark A/B sobre 90 imágenes reales del Campus Fernando May.*

La desactivación de los preprocesadores redundantes no solo incrementó drásticamente la tasa de éxito de lectura en un **63%** al evitar distorsiones en el texto, sino que redujo el costo computacional del reconocimiento a una tercera parte (de 1.27s a 0.39s por frame), haciéndolo altamente viable para ejecución fluida en CPUs estándar de servidores de rango medio de la universidad.

---

### 1.2 Diseño de Arquitectura Física y de Red de la Cámara en Terreno
Para el despliegue del sistema en el punto de control de acceso del Campus Fernando May, se evaluaron dos esquemas de arquitectura física de hardware y red, analizando las restricciones de ancho de banda y latencia:

#### A. Arquitectura Centralizada (Procesamiento en Servidor de Borde con Streaming)
Bajo esta arquitectura, el computador de captura (situado junto a la cámara web o IP en el estacionamiento) actúa únicamente como un nodo de adquisición de video ligero. Transmite el flujo de video en tiempo real a través del protocolo **RTSP** (Real-Time Streaming Protocol) o **HTTP** a un servidor centralizado (PC de procesamiento equipado con GPU dedicada, como la NVIDIA RTX 5070) situado en otro punto de la red local.
* **Ventajas:** Permite ejecutar la inferencia de YOLOv8n y PaddleOCR a máxima velocidad aprovechando la aceleración por hardware (GPU) centralizada, manteniendo el computador de terreno libre de cargas pesadas de cómputo de IA.
* **Desafíos:** Alta dependencia de la estabilidad y ancho de banda de la red local para transmitir video continuo a 30 FPS en alta resolución, lo que puede causar pérdida de frames en redes Wi-Fi saturadas.

#### B. Arquitectura en el Borde (Procesamiento Local + Sincronización en la Nube) - *Esquema Implementado*
Este enfoque utiliza un computador portátil o mini-PC industrial local (en terreno) que se conecta físicamente mediante un cable Ethernet RJ45 PoE (Power over Ethernet) a una cámara IP o mediante un cable USB Activo a una cámara web. Este nodo de borde realiza localmente todo el procesamiento de visión por computadora (detección de patentes YOLOv8n y lectura de caracteres PaddleOCR) y se conecta a internet (vía red local o datos móviles 4G/5G).
* **Consumo Eficiente de Datos:** Al realizar la inferencia de forma local, el sistema no requiere transmitir video por internet. Cuando un vehículo activa el sensor visual y su patente es leída con éxito, el sistema envía únicamente un payload JSON ligero de pocos bytes y la imagen recortada de la placa (aproximadamente 150 KB en formato JPG comprimido) a la base de datos de **Supabase** en la nube.
* **Trazabilidad e Integridad:** Los datos se registran en tiempo real y el dashboard web del encargado (PC 1 en la torre o casa) se actualiza instantáneamente vía WebSockets sin necesidad de estar físicamente en el estacionamiento.

---

### 1.3 Normalización y Simplificación del Modelo de Datos (Enfoque de Calidad 3NF)
Durante la fase de auditoría del modelamiento de base de datos relacional PostgreSQL (Supabase), se identificó una oportunidad de optimización de normalización en la tabla `incidencias`. Originalmente, la tabla almacenaba de forma redundante las columnas `zona_id` y `vehiculo_patente` de manera paralela a la llave foránea `acceso_id`. 

Desde el punto de vista de la teoría de bases de datos relacionales, esto constituía una violación de la **Tercera Forma Normal (3NF)** por la presencia de dependencias transitivas:
$$\text{id} \rightarrow \text{acceso\_id} \rightarrow \text{vehiculo\_patente}$$
$$\text{id} \rightarrow \text{acceso\_id} \rightarrow \text{zona\_id}$$

Para asegurar la rigurosidad académica del proyecto de título se proponen dos enfoques de justificación:
1. **Normalización Estricta (3NF):** Remover las columnas `zona_id` y `vehiculo_patente` de la tabla `incidencias`, resolviendo dichos campos en las consultas de frontend mediante operaciones de agregación y uniones (`JOIN`) con la tabla `accesos`. Esto previene anomalías de actualización de datos y reduce la redundancia.
2. **Desnormalización Controlada (Diseño Flexible):** Mantener las columnas como opcionales (`NULL`) justificando su existencia para registrar incidencias de carácter general e independiente en el estacionamiento que no cuenten con una entrada/salida registrada (por ejemplo, reportar un bache en la calzada de la "Zona A" o un vehículo estacionado sin patente visible).

---

## 2. Referencias Bibliográficas (Norma IEEE) y Enlaces para Investigación

Puedes utilizar las siguientes referencias formales en la bibliografía de tu tesis:

### [1] Detección de Objetos en Tiempo Real (YOLOv8)
* **Cita IEEE:** G. Jocher, A. Chaurasia, and J. Qiu, "YOLO by Ultralytics," Jan. 2023. [Online]. Available: https://github.com/ultralytics/ultralytics
* **Referencia de consulta:** Documentación oficial y repositorio de Ultralytics para el entrenamiento de YOLOv8n en el dataset de placas patentes.
* **Enlace:** [Ultralytics GitHub Repository](https://github.com/ultralytics/ultralytics)

### [2] Reconocimiento Óptico de Caracteres (PaddleOCR)
* **Cita IEEE:** Y. Du et al., "PP-OCR: A practical ultra-lightweight OCR system," *arXiv preprint arXiv:2009.09941*, Sep. 2020. [Online]. Available: https://github.com/PaddlePaddle/PaddleOCR
* **Referencia de consulta:** Documentación del motor PP-OCR y las optimizaciones de inferencia sobre CPU mediante PaddlePaddle.
* **Enlace:** [PaddleOCR GitHub Repository](https://github.com/PaddlePaddle/PaddleOCR)

### [3] Framework de Aprendizaje Profundo (PyTorch)
* **Cita IEEE:** A. Paszke et al., "PyTorch: An imperative style, high-performance deep learning library," in *Advances in Neural Information Processing Systems 32 (NeurIPS)*, 2019, pp. 8024–8035. [Online]. Available: https://pytorch.org
* **Referencia de consulta:** Soporte CUDA 12.8 para GPU de arquitectura Blackwell (RTX 5070) mediante versiones de compilación cu128.
* **Enlace:** [PyTorch Official Website](https://pytorch.org)

### [4] Procesamiento Digital de Imágenes (OpenCV)
* **Cita IEEE:** G. Bradski, "The OpenCV Library," *Dr. Dobb's Journal of Software Tools*, vol. 25, no. 11, pp. 120–125, Nov. 2000. [Online]. Available: https://opencv.org
* **Referencia de consulta:** Operaciones de re-dimensionamiento bicúbico inteligente (Smart Resize BGR), codificación a JPG binario en memoria y captura de cámara mediante controladores de hardware DirectShow (`CAP_DSHOW`).
* **Enlace:** [OpenCV Official Website](https://opencv.org)

### [5] Backend-as-a-Service en Tiempo Real (Supabase)
* **Cita IEEE:** Supabase Inc., "Supabase Open Source Firebase Alternative," 2020. [Online]. Available: https://supabase.com
* **Referencia de consulta:** Mecanismos de persistencia relacional PostgreSQL, autenticación de usuarios basada en roles, web sockets en tiempo real para actualización de dashboards y sistema de almacenamiento de objetos binarios (Supabase Storage).
* **Enlace:** [Supabase Documentation](https://supabase.com/docs)

### [6] Desarrollo Frontend Moderno (React + Vite)
* **Cita IEEE:** React Core Team, "React: A JavaScript library for building user interfaces," 2013. [Online]. Available: https://react.dev
* **Referencia de consulta:** Implementación de flujos de renderizado reactivos y comunicación asíncrona mediante hooks en React 18.
* **Enlace:** [React Official Documentation](https://react.dev)

---

## 3. Guía de Uso del Documento
1. **Para el Capítulo de Desarrollo/Implementación:** Utiliza las secciones 1.1 y 1.2 para fundamentar las optimizaciones de software (por qué desactivaste los preprocesadores de PaddleX para acelerar un 3x el OCR) y la configuración de red física del punto de control del Campus Fernando May.
2. **Para el Capítulo de Modelamiento de Datos:** Utiliza la sección 1.3 para justificar teóricamente por qué mantuviste las relaciones nulas en `incidencias` o cómo planificas normalizar a 3NF en las conclusiones.
3. **Para la Bibliografía:** Copia directamente los bloques de la sección 2 del formato IEEE al apartado bibliográfico de tu tesis.
