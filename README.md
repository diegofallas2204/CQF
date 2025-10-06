# 🚚 Courier Quest

**Courier Quest** es un proyecto académico desarrollado como simulador de entregas urbanas, implementado en **Python (3.11+) con Pygame**.  
El juego combina estructuras de datos avanzadas, gestión de clima dinámico y control de pedidos en tiempo real.

---

## 🎯 Objetivo del juego

El jugador asume el rol de un repartidor que debe cumplir pedidos dentro de una ciudad simulada, enfrentando factores como el clima, la fatiga y el tiempo límite.  
El objetivo es **alcanzar la meta de ganancias (`goal`) antes de que el tiempo se agote**, manejando el inventario de pedidos y optimizando el recorrido.

---

## 🧩 Estructura del proyecto

CQF-main/
│
├── api_cache/ # Archivos de caché descargados desde la API
│ ├── city.json
│ ├── orders.json
│ └── weather.json
│
├── Data/ # Datos locales de respaldo (modo offline)
│ ├── API.py
│ ├── city.json
│ ├── orders.json
│ ├── weather.json
│ └── ...
│
├── DataStructure/ # Estructuras de datos implementadas desde cero
│ ├── DoublyLinkedList.py
│ ├── PriorityQueue.py
│ ├── SortingAlgorithms.py
│ └── Stack.py
│
├── Entities/ # Clases principales del juego
│ ├── City.py
│ ├── Order.py
│ └── Player.py
│
├── Management/ # Controladores y gestores del juego
│ ├── APIManager.py
│ ├── CacheManager.py
│ ├── FileManager.py
│ ├── GameStateManager.py
│ ├── Inventory.py
│ ├── OrderManager.py
│ ├── ScoreCalculator.py
│ └── WeatherManager.py
│
├── State/ # Definición de estados del juego
│ ├── GameState.py
│ ├── OrderState.py
│ └── PlayerState.py
│
├── Game.py # Lógica principal del juego
├── Main.py # Punto de entrada (main loop)
└── README.md # ← Este archivo

---

## ⚙️ Instalación y ejecución

### Requisitos:
- Python **3.11 o superior**
- Librería **pygame 2.6+**
- Conexión a Internet (opcional, para modo en línea)

### Instalación:
```bash
pip install pygame requests

```
---

### Ejecución:

```bash
python Main.py
```
---
## 🎮 Controles del juego
| Tecla     | Acción                                      |
| --------- | ------------------------------------------- |
| `W/A/S/D` | Moverse                                     |
| `ESPACIO` | Abrir menú de pedidos                       |
| `E`       | Aceptar o recoger pedido                    |
| `C`       | Cancelar pedido actual                      |
| `U`       | Deshacer último movimiento                  |
| `I`       | Cambiar modo de ordenamiento del inventario |
| `N / P`   | Navegar entre pedidos del inventario        |
| `ESC`     | Pausar / Reanudar                           |
| `Q`       | Salir del juego                             |


API y modo offline

El juego se conecta a la API de TigerCity, que proporciona:

/city/map → mapa y metadatos de la ciudad

/city/jobs → pedidos disponibles

/city/weather → condiciones climáticas dinámicas

Si no hay conexión, el sistema usa:

Archivos en caché (api_cache/)

Archivos locales (Data/)

Esto garantiza que el juego funcione incluso sin Internet.

---
## 📚 Estructuras de datos implementadas
| Estructura / Clase                               | Uso                                                           | Complejidad promedio                       |
| ------------------------------------------------ | ------------------------------------------------------------- | ------------------------------------------ |
| `DoublyLinkedList`                               | Inventario navegable (pedidos aceptados).                     | Inserción/eliminación O(1), búsqueda O(n). |
| `PriorityQueue` (heapq)                          | Cola de prioridad para pedidos disponibles.                   | Inserción/extracción O(log n).             |
| `Stack`                                          | Sistema de deshacer (historial de movimientos).               | Push/pop O(1).                             |
| `SortingAlgorithms` (`quick_sort`, `merge_sort`) | Ordenar pedidos e inventario (por prioridad, pago, deadline). | O(n log n) promedio.                       |
| `dict` (hash table)                              | Índices de pedidos (`all_orders`, `orders_by_id`).            | Búsqueda/actualización O(1).               |

---
## Principales gestores
| Módulo             | Función                                                                |
| ------------------ | ---------------------------------------------------------------------- |
| `OrderManager`     | Administra todos los pedidos (carga, estado, expiración).              |
| `Inventory`        | Controla el inventario del jugador usando lista doblemente enlazada.   |
| `GameStateManager` | Sistema de deshacer mediante pila.                                     |
| `WeatherManager`   | Simula condiciones climáticas y efectos sobre velocidad y resistencia. |
| `ScoreCalculator`  | Calcula puntaje final según rendimiento.                               |


## Conceptos  implementados
-Estructuras de datos personalizadas
-Persistencia local con caché
-Gestión de estados finitos
-Probabilidades de transición de clima
-Arquitectura modular en paquetes Python
-Cumplimiento de PEP8 y tipado estático (typing)

---
Autores

Nombres: Santiago Azofeifa Benavides, Carlos Conejo Pearzon, Luis Fallas Brizuela
Proyecto: Primer Proyecto – Courier Quest
Curso: Estructura de Datos
Año: 2025