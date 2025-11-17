# Courier Quest

**Courier Quest** es un proyecto académico desarrollado como simulador de entregas urbanas, implementado en **Python (3.11+) con Pygame**.  
El juego combina estructuras de datos avanzadas, gestión de clima dinámico y control de pedidos en tiempo real.

---

## Novedades (Fase 2)
- Menú de dificultad: Fácil / Medio / Difícil (con IA y planificación).
- Agente CPU/IA con distintos comportamientos según dificultad.
- Menú de selección de pedidos con ordenamiento por:
  - prioridad, deadline, pago (teclas 1/2/3).
- Sistema de deshacer acciones.
- Inventario navegable con lista doblemente enlazada.
- Guardado/carga rápida de partida y tabla de puntajes.
- HUD mejorado con clima, tiempo restante, estadísticas y previsualización de puntaje.

---

## Objetivo del juego

Asumes el rol de un repartidor que debe cumplir pedidos dentro de una ciudad simulada, enfrentando factores como el clima, la fatiga y el tiempo límite.  
El objetivo es **alcanzar la meta de ganancias (`goal`) antes de que el tiempo se agote**, gestionando el inventario de pedidos y optimizando los recorridos.

---

## Estructura del proyecto

```
CQF-main/
│
├── api_cache/                # Archivos de caché descargados desde la API
│   ├── city.json
│   ├── orders.json
│   └── weather.json
│
├── Data/                     # Datos locales de respaldo (modo offline)
│   ├── API.py
│   ├── city.json
│   ├── orders.json
│   ├── weather.json
│   └── ...
│
├── DataStructure/            # Estructuras de datos implementadas desde cero
│   ├── DoublyLinkedList.py
│   ├── PriorityQueue.py
│   ├── SortingAlgorithms.py
│   └── Stack.py
│
├── Entities/                 # Clases principales del juego
│   ├── City.py
│   ├── Order.py
│   └── Player.py
│
├── Management/               # Controladores y gestores del juego
│   ├── AIManager.py          # Lógica del agente CPU/IA y sus estrategias
│   ├── APIManager.py         # Acceso a TigerCity/TigerDS API
│   ├── CacheManager.py       # Caché en disco de respuestas de API
│   ├── FileManager.py        # Guardado/carga de partidas y puntajes
│   ├── GameStateManager.py   # Sistema de deshacer (historial)
│   ├── Graph_builder.py      # (graph_builder.py) Construcción de grafo/ruteo
│   ├── Inventory.py          # Inventario (lista doblemente enlazada)
│   ├── OrderManager.py       # Gestión integral de pedidos
│   ├── ScoreCalculator.py    # Cálculo de puntuación final y bonus/penalizaciones
│   └── WeatherManager.py     # Simulación de clima y efectos de movilidad
│
├── State/                    # Definición de estados del juego
│   ├── GameState.py
│   ├── OrderState.py
│   └── PlayerState.py
│
├── saves/                    # Partidas guardadas y puntajes locales
├── tests/                    # Pruebas automáticas del proyecto
├── fixtures/                 # Datos/configuraciones de prueba
├── docs/                     # Documentación adicional del proyecto
│
├── difficulty_menu.png       # Recurso gráfico (menú de dificultad)
├── main_menu.png             # Recurso gráfico (menú principal)
│
├── Courier Quest Parte 2.pdf # Documento de especificación/progreso del proyecto
│
├── Game.py                   # Lógica principal del juego
├── Main.py                   # Punto de entrada (main loop)
├── .gitignore                # Reglas para Git
└── README.md                 # ← Este archivo
```

---

## Instalación y ejecución

### Requisitos:
- Python **3.11 o superior**
- Librerías: **pygame 2.6+**, **requests**
- Conexión a Internet (opcional, para modo en línea)

### Instalación:
```bash
pip install pygame requests
```

### Ejecución:
```bash
python Main.py
```

---

## Controles del juego

- Movimiento:
  - `W/A/S/D` o flechas `↑/↓/←/→` para moverse.
- Pedidos e inventario:
  - `ESPACIO`: abrir menú de pedidos.
  - `E`: aceptar pedido cercano (si no hay activo) o recogerlo (si ya fue aceptado y estás junto al pickup).
  - `C`: cancelar pedido actual.
  - `U`: deshacer última acción.
  - `I`: alternar ordenamiento del inventario (prioridad → deadline → pago).
  - `N / P`: navegar entre pedidos del inventario.
- Guardado, carga, pausa y salida:
  - `F5`: guardar partida rápida.
  - `F9`: cargar partida rápida.
  - `ESC`: pausar / reanudar.
  - `Q`: salir del juego.

Controles contextuales:
- Menú de dificultad:
  - `1` = Fácil, `2` = Medio, `3` = Difícil, `ESC` = Volver.
- Selección de pedidos (overlay):
  - `↑/↓`: navegar la lista, `ENTER`: aceptar seleccionado, `R` o `ESC`: cerrar.
  - `1`: ordenar por prioridad, `2`: por deadline, `3`: por pago.
- Pantalla de fin de juego (Victoria/Derrota):
  - `S`: guardar puntaje, `ESPACIO`: volver al menú, `Q` o `ESC`: salir.

---

## API y modo offline

El juego se conecta a la API de TigerCity/TigerDS, que proporciona:
- `/city/map` → mapa y metadatos de la ciudad
- `/city/jobs` → pedidos disponibles
- `/city/weather` → condiciones climáticas dinámicas

Si no hay conexión, el sistema usa:
- Archivos en caché (`api_cache/`)
- Archivos locales (`Data/`)

Esto garantiza que el juego funcione incluso sin Internet.

---

## Estructuras de datos implementadas

| Estructura / Clase                               | Uso                                                           | Complejidad promedio                       |
| ------------------------------------------------ | ------------------------------------------------------------- | ------------------------------------------ |
| `DoublyLinkedList`                               | Inventario navegable (pedidos aceptados).                     | Inserción/eliminación O(1), búsqueda O(n). |
| `PriorityQueue` (heapq)                          | Cola de prioridad para pedidos disponibles.                   | Inserción/extracción O(log n).             |
| `Stack`                                          | Sistema de deshacer (historial de movimientos).               | Push/pop O(1).                             |
| `SortingAlgorithms` (`quick_sort`, `merge_sort`) | Ordenar pedidos e inventario (por prioridad, pago, deadline). | O(n log n) promedio.                       |
| `dict` (hash table)                              | Índices de pedidos (`all_orders`, `orders_by_id`).            | Búsqueda/actualización O(1).               |

---

## Principales gestores

| Módulo             | Función                                                                 |
| ------------------ | ----------------------------------------------------------------------- |
| `OrderManager`     | Administra todos los pedidos (carga, estado, expiración).               |
| `Inventory`        | Controla el inventario del jugador usando lista doblemente enlazada.    |
| `GameStateManager` | Sistema de deshacer mediante pila.                                      |
| `WeatherManager`   | Simula condiciones climáticas y efectos sobre velocidad y resistencia.  |
| `ScoreCalculator`  | Calcula puntaje final según rendimiento.                                |
| `AIManager`        | Control del agente CPU/IA (estrategias por dificultad, A*, heurísticas)|
| `graph_builder`    | Construcción del grafo de navegación para planificación de rutas.       |

---

## Modo IA y dificultades

- Fácil: movimiento/decisiones simples (aleatoriedad controlada).
- Medio: heurísticas (distancia, pago, deadline).
- Difícil: planificación con grafo (p. ej. A*) y decisiones más óptimas.

Selecciona la dificultad desde el menú inicial:
- `ESPACIO` en el menú → luego `1/2/3` para iniciar en Fácil/Medio/Difícil.

---

## Ejecución de pruebas automáticas

Si el proyecto incluye pruebas:
- Con unittest:
```bash
python -m unittest discover tests
```
- Con pytest (instálalo con `pip install pytest`):
```bash
pytest
```

---

## Documentación

- Documentación adicional en la carpeta `docs/`.
- El archivo “Courier Quest Parte 2.pdf” resume especificaciones y avances del proyecto.

---

## Conceptos implementados

- Estructuras de datos personalizadas
- Persistencia local con caché
- Gestión de estados finitos
- Probabilidades de transición de clima
- Arquitectura modular en paquetes Python
- Cumplimiento de PEP8 y tipado estático (`typing`)

---

## Recursos gráficos

- `main_menu.png` (menú principal)
- `difficulty_menu.png` (menú de dificultad)

Puedes usar estas imágenes en la documentación o para vista previa del juego.

---

## Autores

- Santiago Azofeifa Benavides  
- Carlos Conejo Pearzon  
- Luis Fallas Brizuela

**Proyecto:** Primer Proyecto – Courier Quest  
**Curso:** Estructura de Datos  
**Universidad Nacional de Costa Rica**  
**Año:** 2025

---
