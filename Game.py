import pygame
import time
from typing import List, Dict, Any, Optional, Tuple
from Management.APIManager import APIManager
from Management.FileManager import FileManager
from Management.CacheManager import CacheManager
from Management.WeatherManager import WeatherManager
from Entities.Player import Player
from Entities.City import City
from Management.Inventory import Inventory
from DataStructure.DoublyLinkedList import DoublyLinkedList
from Management.OrderManager import OrderManager
from Management.GameStateManager import GameStateManager
from Management.ScoreCalculator import ScoreCalculator
from State.GameState import GameState
from State.PlayerState import PlayerState
from State.OrderState import OrderState
from datetime import datetime
from copy import deepcopy
import os
import inspect


class Game:
    """
    Clase Game extendida con todas las funcionalidades de Fase 2.
    Incluye gestión avanzada de inventario, pedidos y sistema de deshacer.
    """

    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        # Inicialización básica (Fase 1)
        pygame.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Courier Quest - Phase 2")
        self.clock = pygame.time.Clock()

        # APIManager ahora delega en API.py (que normaliza/desanida)
        self.api_manager = APIManager(
            base_url="https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"
        )
        self.file_manager = FileManager()
        self.cache_manager = CacheManager()

        self.weather_manager = WeatherManager()

        # Estado del juego
        self.running = True
        self.state = GameState.MENU
        self.fps = 60

        # Componentes básicos
        self.player = Player()
        self.city = City()

        # Nuevos componentes de Fase 2
        self.inventory = Inventory()
        self.order_manager = OrderManager()
        self.state_manager = GameStateManager()
        self.score_calculator = ScoreCalculator()

        # Control de tiempo
        self.game_start_time = 0.0
        self.game_duration = 900.0  # 15 minutos
        self.current_time = 0.0
        self.last_movement_time = 0.0
        self.movement_cooldown = 1.0

        # UI y controles
        self.selected_order_index = 0  # Para navegación en menú de pedidos
        self.inventory_sort_mode = "priority"  # priority, deadline, payout

        # Colores
        self.colors = {
            "BLACK": (0, 0, 0),
            "WHITE": (255, 255, 255),
            "GREEN": (0, 255, 0),
            "RED": (255, 0, 0),
            "BLUE": (0, 0, 255),
            "GRAY": (128, 128, 128),
            "YELLOW": (255, 255, 0),
            "ORANGE": (255, 165, 0),
            "PURPLE": (128, 0, 128),
            "CYAN": (0, 255, 255),
            "DARK_GREEN": (0, 128, 0),
            "DARK_RED": (128, 0, 0),
        }

    def handle_events(self):
        """Manejo extendido de eventos"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    self._handle_menu_input(event.key)

                elif self.state == GameState.PLAYING:
                    self._handle_game_input(event.key)

                elif self.state == GameState.ORDER_SELECTION:
                    self._handle_order_selection_input(event.key)

                elif self.state == GameState.PAUSED:
                    self._handle_pause_input(event.key)

                elif self.state in [GameState.VICTORY, GameState.GAME_OVER]:
                    self._handle_game_end_input(event.key)
                

    def _handle_menu_input(self, key):
        """Manejo de input en menú"""
        if key == pygame.K_SPACE:
            self.start_game()
        elif key in [pygame.K_q, pygame.K_ESCAPE]:
            self.running = False

    def _handle_game_input(self, key):
        """Manejo de input durante el juego"""
        if key == pygame.K_ESCAPE:
            self.state = GameState.PAUSED
        elif key == pygame.K_q:
            self.running = False

        # Movimiento
        elif key in [pygame.K_w, pygame.K_UP]:
            self._attempt_move(0, -1)
        elif key in [pygame.K_s, pygame.K_DOWN]:
            self._attempt_move(0, 1)
        elif key in [pygame.K_a, pygame.K_LEFT]:
            self._attempt_move(-1, 0)
        elif key in [pygame.K_d, pygame.K_RIGHT]:
            self._attempt_move(1, 0)

        # Funcionalidades nuevas
        elif key == pygame.K_SPACE:  # Abrir menú de pedidos
            self.state = GameState.ORDER_SELECTION
        elif key == pygame.K_i:  # Mostrar inventario
            self._toggle_inventory_sort()
        elif key == pygame.K_u:  # Deshacer último movimiento
            self._undo_last_action()
        elif key == pygame.K_n:  # Navegar inventario siguiente
            self.inventory.navigate_next()
        elif key == pygame.K_p:  # Navegar inventario anterior
            self.inventory.navigate_prev()
        elif key == pygame.K_c:  # Cancelar pedido activo
            self._cancel_current_order()
        elif key == pygame.K_e:
            # Si no hay pedido activo, intenta aceptar uno cercano
            if not self.inventory.get_current_order():
                self._attempt_accept_nearby_order()
            else:
                # Si ya hay pedido activo, intenta recogerlo
                self._attempt_pickup_current_order()

    def _handle_order_selection_input(self, key):
        """Manejo de input en selección de pedidos"""
        available_orders = self._get_sorted_available_orders()

        if key == pygame.K_ESCAPE:
            self.state = GameState.PLAYING
        elif key == pygame.K_UP and self.selected_order_index > 0:
            self.selected_order_index -= 1
        elif (
            key == pygame.K_DOWN
            and self.selected_order_index < len(available_orders) - 1
        ):
            self.selected_order_index += 1
        elif key == pygame.K_RETURN:  # Aceptar pedido
            self._accept_selected_order()
        elif key == pygame.K_r:  # Rechazar/cancelar (cerrar)
            self.state = GameState.PLAYING
        elif key == pygame.K_1:  # Ordenar por prioridad
            self.inventory_sort_mode = "priority"
            self.selected_order_index = 0
        elif key == pygame.K_2:  # Ordenar por deadline
            self.inventory_sort_mode = "deadline"
            self.selected_order_index = 0
        elif key == pygame.K_3:  # Ordenar por pago
            self.inventory_sort_mode = "payout"
            self.selected_order_index = 0

    def _handle_pause_input(self, key):
        """Manejo de input en pausa"""
        if key == pygame.K_ESCAPE:
            self.state = GameState.PLAYING
        elif key == pygame.K_q:
            self.running = False

    def _handle_game_end_input(self, key):
        """Manejo de input en fin de juego"""
        if key == pygame.K_SPACE:
            self.state = GameState.MENU
            self._reset_game()
        elif key in [pygame.K_q, pygame.K_ESCAPE]:
            self.running = False

    def _attempt_move(self, dx: int, dy: int):
        """Intenta mover al jugador y guarda estado"""
        # Guardar estado antes del movimiento
        self.state_manager.save_state(self)

        current_x, current_y = self.player.position
        new_x, new_y = current_x + dx, current_y + dy

        if self.city.is_walkable(new_x, new_y):
            surface_weight = self.city.get_surface_weight(new_x, new_y)
            # CLIMA: pasar multiplicador de velocidad y costo extra de stamina por celda
            success = self.player.move_to(
                (new_x, new_y),
                climate_multiplier=self.weather_manager.get_speed_multiplier(),
                surface_weight=surface_weight,
                reputation_multiplier=1.0,
                stamina_extra_cost=self.weather_manager.get_stamina_penalty_per_cell(),
            )

            if success:
                self.last_movement_time = time.time()
                self._check_location_interactions()
            else:
                # Si no se pudo mover, remover el estado guardado
                try:
                    self.state_manager.history.pop()
                except Exception:
                    pass
        else:
            # Movimiento inválido, remover estado guardado
            try:
                self.state_manager.history.pop()
            except Exception:
                pass

    def _get_sorted_available_orders(self):
        """Devuelve la lista de pedidos disponibles según el modo actual."""
        if self.inventory_sort_mode == "priority":
            return self.order_manager.get_available_orders_by_priority()
        elif self.inventory_sort_mode == "deadline":
            return self.order_manager.get_available_orders_by_deadline()
        elif self.inventory_sort_mode == "payout":
            return self.order_manager.get_available_orders_by_payout()
        else:
            return self.order_manager.get_available_orders_by_priority()

    def _check_location_interactions(self):
        x, y = self.player.position
        current_order = self.inventory.get_current_order()

        if current_order:
            # Pickup solo con tecla 'E', no automático
            # Verificar si estamos a una casilla de distancia del punto de entrega
            if (
                current_order.state in [OrderState.PICKED_UP, OrderState.ACCEPTED]
                and self.city.calculate_manhattan_distance(
                    (x, y), current_order.dropoff
                )
                == 1
            ):
                self._deliver_current_order()

    def _deliver_current_order(self):
        """Entrega el pedido actual"""
        current_order = self.inventory.get_current_order()
        if not current_order:
            return

        delivered_order = self.order_manager.deliver_order(current_order.id)
        if delivered_order:
            # Calcular pago (aquí se aplicaría multiplicador de reputación)
            payout = delivered_order.payout
            self.player.add_earnings(payout)

            # Remover del inventario y sincronizar peso
            self.inventory.remove_order(delivered_order.id)
            self.player.inventory_weight = self.inventory.current_weight

            print(f"¡Pedido {delivered_order.id} entregado! +${payout}")
            print(f"Ingresos totales: ${self.player.total_earnings}")

    def _toggle_inventory_sort(self):
        """Cambia el modo de ordenamiento del inventario y actualiza la navegación"""
        modes = ["priority", "deadline", "payout"]
        current_index = modes.index(self.inventory_sort_mode)
        self.inventory_sort_mode = modes[(current_index + 1) % len(modes)]
        print(f"Inventario ordenado por: {self.inventory_sort_mode}")

        # Obtener la lista ordenada según el modo
        if self.inventory_sort_mode == "priority":
            sorted_orders = self.inventory.get_orders_by_priority()
        elif self.inventory_sort_mode == "deadline":
            sorted_orders = self.inventory.get_orders_by_deadline()
        elif self.inventory_sort_mode == "payout":
            sorted_orders = self.inventory.get_orders_by_payout()
        else:
            sorted_orders = self.inventory.orders.to_list()

        # Reconstruir la lista enlazada en el nuevo orden
        self.inventory.orders = DoublyLinkedList()
        self.inventory.orders_by_id.clear()
        self.inventory.current_weight = 0.0
        for order in sorted_orders:
            self.inventory.orders.append(order)
            self.inventory.orders_by_id[order.id] = order
            self.inventory.current_weight += order.weight

        # Resetear navegación al primer elemento
        self.inventory.reset_navigation()

    def _undo_last_action(self):
        """Deshace la última acción"""
        if self.state_manager.undo_last_action(self):
            print("Acción deshecha")
        else:
            print("No hay acciones para deshacer")

    def _accept_selected_order(self):
        """Acepta el pedido seleccionado (con restricciones: solo 1 pedido activo)"""
        available_orders = self.order_manager.get_available_orders_by_priority()

        print(f"Total pedidos disponibles: {len(available_orders)}")
        print(f"Índice seleccionado: {self.selected_order_index}")

        if 0 <= self.selected_order_index < len(available_orders):
            selected_order = available_orders[self.selected_order_index]

            print(f"Intentando aceptar pedido {selected_order.id}")
            print(f"Estado actual del pedido: {selected_order.state}")
            print(f"Peso actual inventario: {self.inventory.current_weight:.1f}")
            print(f"Peso del pedido: {selected_order.weight}")
            print(f"Capacidad máxima: {self.inventory.max_weight}")

            # Verificar si ya hay pedido activo en todo el sistema
            for o in self.order_manager.all_orders.values():
                if o.state in [OrderState.ACCEPTED, OrderState.PICKED_UP]:
                    print(
                        f"Ya tienes un pedido activo ({o.id}). Cancélalo o entrégalo antes de aceptar otro."
                    )
                    print("Error: No se pudo aceptar el pedido")
                    return

            # Verificar capacidad
            if self.inventory.can_add_order(selected_order):
                print("Capacidad OK, solicitando aceptar al OrderManager...")

                # Solicitar al OrderManager que acepte (quitará de la cola)
                order_for_accept = self.order_manager.accept_order(selected_order.id)
                if order_for_accept is None:
                    print(
                        "Error: OrderManager no permitió aceptar (posible pedido activo o cambio de estado)."
                    )
                    print("Error: No se pudo aceptar el pedido")
                    return

                # Agregar al inventario (Inventory.set state to ACCEPTED si procede)
                if self.inventory.add_order(order_for_accept):
                    # Sincronizar peso del jugador
                    self.player.inventory_weight = self.inventory.current_weight
                    print(f"✓ Pedido {order_for_accept.id} aceptado exitosamente")
                    print(
                        f"Peso jugador actualizado a: {self.player.inventory_weight:.1f}kg"
                    )
                    self.state = GameState.PLAYING
                    return
                else:
                    # Si no se pudo agregar, revertir la acción: devolver a disponibles
                    order_for_accept.state = OrderState.AVAILABLE
                    self.order_manager.available_orders.push(
                        order_for_accept, order_for_accept.priority
                    )
                    print("Error: No se pudo agregar al inventario (reverting state)")
            else:
                print("No hay capacidad en inventario")
        else:
            print(
                f"Índice de pedido inválido: {self.selected_order_index} / {len(available_orders)}"
            )

        print("Error: No se pudo aceptar el pedido")

    def _cancel_current_order(self):
        """Cancela el pedido activo en inventario y aplica penalización de reputación/earnings"""
        current_order = self.inventory.get_current_order()
        if not current_order:
            print("No hay pedido activo para cancelar.")
            return

        # Solo cancelar si está ACCEPTED o PICKED_UP
        if current_order.state not in [OrderState.ACCEPTED, OrderState.PICKED_UP]:
            print(
                "El pedido actual no puede cancelarse (no está en estado aceptado/recogido)."
            )
            return

        cancelled = self.order_manager.cancel_order(current_order.id)
        if cancelled:
            # Remover del inventario
            self.inventory.remove_order(current_order.id)
            self.player.inventory_weight = self.inventory.current_weight

            # Aplicar penalización: reputación y deducción de earnings (puedes ajustar valores)
            penalty_rep = 10
            penalty_money = 50
            self.player.reputation = max(0, self.player.reputation - penalty_rep)
            self.player.total_earnings = max(
                0, self.player.total_earnings - penalty_money
            )

            # Opcional: NOTA: el pedido queda en estado CANCELLED en all_orders (no regresa a available)
            print(
                f"Pedido {current_order.id} cancelado. -{penalty_rep} reputación, -${penalty_money}."
            )
        else:
            print("No se pudo cancelar el pedido (estado inválido).")

    def _attempt_pickup_current_order(self):
        """Intenta recoger el pedido actual si está a una casilla de distancia"""
        x, y = self.player.position
        current_order = self.inventory.get_current_order()
        if (
            current_order
            and current_order.state == OrderState.ACCEPTED
            and self.city.calculate_manhattan_distance((x, y), current_order.pickup)
            == 1
        ):
            if self.order_manager.pickup_order(current_order.id):
                print(f"¡Pedido {current_order.id} recogido!")

    def _attempt_accept_nearby_order(self):
        """Intenta aceptar un pedido disponible si está a una casilla de distancia del pickup"""
        x, y = self.player.position
        # Solo permite aceptar si no hay pedido activo
        if any(
            o.state in [OrderState.ACCEPTED, OrderState.PICKED_UP]
            for o in self.order_manager.all_orders.values()
        ):
            print(
                "Ya tienes un pedido activo. Cancélalo o entrégalo antes de aceptar otro."
            )
            return

        # Buscar pedidos disponibles cerca
        for order in self.order_manager.get_available_orders_by_priority():
            if self.city.calculate_manhattan_distance((x, y), order.pickup) == 1:
                # Verificar capacidad
                if self.inventory.can_add_order(order):
                    order_for_accept = self.order_manager.accept_order(order.id)
                    if order_for_accept and self.inventory.add_order(order_for_accept):
                        self.player.inventory_weight = self.inventory.current_weight
                        print(f"✓ Pedido {order_for_accept.id} aceptado exitosamente")
                        return
                else:
                    print("No hay capacidad en inventario para aceptar el pedido.")
                    return
        print("No hay pedidos disponibles cerca para aceptar.")

    def start_game(self):
        """Inicia nueva partida y abre inmediatamente el menú de pedidos"""
        self.game_start_time = time.time()
        self.current_time = 0.0
        self.last_movement_time = time.time()

        # Reiniciar componentes
        self.player = Player(start_position=(1, 1))
        self.inventory = Inventory()
        self.state_manager.clear_history()

        # Actualizar pedidos disponibles
        self.order_manager.update_available_orders(0.0)

        # Inicializar configuración de clima (API/cache/file o fallback)
        self.refresh_weather()
        # --- DEBUG: acelera el clima para probar en 10–15 s con transición de 2 s ---
        try:
            self.weather_manager._rand_burst = lambda: 12   # cada ~12 s
            self.weather_manager._rand_transition = lambda: 2
            # si ya se inicializó una ráfaga larga, forzamos que la actual termine pronto:
            self.weather_manager._burst_dur = 12
            self.weather_manager._t = min(self.weather_manager._t, 11.0)
        except Exception:
            pass
        # --- fin DEBUG ---


        # Debug: Verificar que hay pedidos disponibles
        available = self.order_manager.get_available_orders_by_priority()
        print(f"Juego iniciado con {len(available)} pedidos disponibles")
        for order in available:
            print(f"  - {order.id}: prioridad {order.priority}, pago ${order.payout}")

        # Asegurar que el peso del inventario del jugador esté sincronizado
        self.player.inventory_weight = self.inventory.current_weight

        # Abrir directamente el menú de selección de pedidos
        self.state = GameState.ORDER_SELECTION
        self.selected_order_index = 0
        print("Menú de pedidos abierto automáticamente")

    def _reset_game(self):
        """Resetea el juego para nueva partida"""
        self.player = Player()
        self.inventory = Inventory()
        self.state_manager.clear_history()
        self.selected_order_index = 0
        self.inventory_sort_mode = "priority"

    def update(self, delta_time: float):
        """Actualización extendida del juego"""
        if self.state == GameState.PLAYING:
            self.current_time = time.time() - self.game_start_time

            # Actualizar pedidos disponibles y expirados
            self.order_manager.update_available_orders(self.current_time)
            self.order_manager.update_expired_orders()

            # Avanzar ráfagas y transiciones del clima
            self.weather_manager.update(delta_time)

            # Recuperación de resistencia
            current_time = time.time()
            time_since_movement = current_time - self.last_movement_time

            if time_since_movement > self.movement_cooldown:
                recovery_rate = 2.0
                self.player.recover_stamina(
                    recovery_rate=recovery_rate, delta_time=delta_time
                )

            # Verificar condiciones de juego
            self.check_game_conditions()

    def check_game_conditions(self):
        """Verificación extendida de condiciones"""
        # Victoria por ingresos
        if self.player.total_earnings >= self.city.goal:
            self.state = GameState.VICTORY

        # Derrota por tiempo
        elif self.current_time >= self.game_duration:
            self.state = GameState.GAME_OVER

        # En fases posteriores: verificar derrota por reputación < 20

    def render(self):
        """Renderizado extendido"""
        # Fondo según clima
        bg = self.weather_manager.get_background_color() if self.weather_manager else self.colors["BLACK"]
        self.screen.fill(bg)

        if self.state == GameState.MENU:
            self._render_menu()
        elif self.state == GameState.PLAYING:
            self._render_game()
        elif self.state == GameState.ORDER_SELECTION:
            self._render_order_selection()
        elif self.state == GameState.PAUSED:
            self._render_game()
            self._render_pause_overlay()
        elif self.state in [GameState.VICTORY, GameState.GAME_OVER]:
            self._render_game_end()

        pygame.display.flip()

    def _render_menu(self):
        """Renderiza menú principal"""
        font = pygame.font.Font(None, 74)
        title_text = font.render("Courier Quest - Phase 2", True, self.colors["WHITE"])
        title_rect = title_text.get_rect(center=(self.screen.get_width() // 2, 150))
        self.screen.blit(title_text, title_rect)

        font = pygame.font.Font(None, 36)
        start_text = font.render(
            "Presiona ESPACIO para iniciar", True, self.colors["WHITE"]
        )
        start_rect = start_text.get_rect(center=(self.screen.get_width() // 2, 300))
        self.screen.blit(start_text, start_rect)

        exit_text = font.render(
            "Presiona Q o ESC para salir", True, self.colors["GRAY"]
        )
        exit_rect = exit_text.get_rect(center=(self.screen.get_width() // 2, 350))
        self.screen.blit(exit_text, exit_rect)

        # Mostrar nuevas características
        font = pygame.font.Font(None, 24)
        features = [
            "Nuevas características Fase 2:",
            "• Sistema de inventario avanzado",
            "• Gestión de pedidos con prioridades",
            "• Sistema de deshacer (U)",
            "• Navegación de inventario (N/P)",
            "• Selección de pedidos (ESPACIO)",
        ]

        for i, feature in enumerate(features):
            color = self.colors["YELLOW"] if i == 0 else self.colors["WHITE"]
            text = font.render(feature, True, color)
            self.screen.blit(text, (50, 450 + i * 25))

    def _render_game(self):
        """Renderizado extendido del juego"""
        # Renderizar mapa
        self._render_map()

        # Renderizar pedidos en mapa
        self._render_orders_on_map()

        # Renderizar jugador
        self._render_player()

        # UI extendida
        self._render_extended_ui()

    def _render_map(self):
        """Renderiza el mapa con mejor uso del espacio"""
        if not self.city.tiles:
            return

        # Usar más espacio vertical, dejando menos para UI
        available_height = self.screen.get_height() - 150  # Reducido de 200 a 150
        tile_size = min(
            self.screen.get_width() // self.city.width,
            available_height // self.city.height,
        )

        # Centrar el mapa si es necesario
        map_width = self.city.width * tile_size
        map_height = self.city.height * tile_size
        offset_x = (self.screen.get_width() - map_width) // 2
        offset_y = 10  # Pequeño margen superior

        for y, row in enumerate(self.city.tiles):
            for x, tile_type in enumerate(row):
                rect = pygame.Rect(
                    offset_x + x * tile_size,
                    offset_y + y * tile_size,
                    tile_size,
                    tile_size,
                )

                if tile_type in self.city.blocked_tiles:
                    color = self.colors["GRAY"]
                elif tile_type == "P":
                    color = self.colors["GREEN"]
                else:
                    color = self.colors["WHITE"]

                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, self.colors["BLACK"], rect, 1)

    def _render_orders_on_map(self):
        """Renderiza iconos de pedidos en el mapa con mejor visibilidad

        Reglas aplicadas:
        - Solo pickups de pedidos AVAILABLE muestran círculo azul 'P'.
        - Solo el dropoff del pedido actual (inventario.current) se muestra en rojo 'D'.
        """
        if not self.city.tiles:
            return

        available_height = self.screen.get_height() - 150
        tile_size = min(
            self.screen.get_width() // self.city.width,
            available_height // self.city.height,
        )

        # Calcular offset para centrar mapa
        map_width = self.city.width * tile_size
        offset_x = (self.screen.get_width() - map_width) // 2
        offset_y = 10

        icon_radius = max(6, tile_size // 4)
        font = pygame.font.Font(None, max(14, tile_size // 3))

        # Mostrar pickups SOLO si release_time ya pasó
        current_game_time = self.current_time
        for order in self.order_manager.all_orders.values():
            if (
                order.state == OrderState.AVAILABLE
                and current_game_time >= order.release_time
            ):
                pickup_x, pickup_y = order.pickup
                center_x = offset_x + pickup_x * tile_size + tile_size // 2
                center_y = offset_y + pickup_y * tile_size + tile_size // 2

                pygame.draw.circle(
                    self.screen, self.colors["BLUE"], (center_x, center_y), icon_radius
                )
                pygame.draw.circle(
                    self.screen,
                    self.colors["WHITE"],
                    (center_x, center_y),
                    icon_radius,
                    2,
                )

                text = font.render("P", True, self.colors["WHITE"])
                text_rect = text.get_rect(center=(center_x, center_y))
                self.screen.blit(text, text_rect)

        # SEGUNDO: Mostrar solo el dropoff del pedido aceptado/recogido actual
        current_order = self.inventory.get_current_order()
        if current_order and current_order.state in [
            OrderState.ACCEPTED,
            OrderState.PICKED_UP,
        ]:
            dropoff_x, dropoff_y = current_order.dropoff
            center_x = offset_x + dropoff_x * tile_size + tile_size // 2
            center_y = offset_y + dropoff_y * tile_size + tile_size // 2

            pygame.draw.circle(
                self.screen, self.colors["RED"], (center_x, center_y), icon_radius
            )
            pygame.draw.circle(
                self.screen, self.colors["WHITE"], (center_x, center_y), icon_radius, 2
            )

            # Letra "D" para delivery
            text = font.render("D", True, self.colors["WHITE"])
            text_rect = text.get_rect(center=(center_x, center_y))
            self.screen.blit(text, text_rect)

            # Línea conectando pickup con delivery si fue recogido
            if current_order.state == OrderState.PICKED_UP:
                pickup_center_x = (
                    offset_x + current_order.pickup[0] * tile_size + tile_size // 2
                )
                pickup_center_y = (
                    offset_y + current_order.pickup[1] * tile_size + tile_size // 2
                )
                pygame.draw.line(
                    self.screen,
                    self.colors["YELLOW"],
                    (pickup_center_x, pickup_center_y),
                    (center_x, center_y),
                    3,
                )

    def _render_player(self):
        """Renderiza jugador con coordenadas centradas"""
        if not self.city.tiles:
            return

        available_height = self.screen.get_height() - 150
        tile_size = min(
            self.screen.get_width() // self.city.width,
            available_height // self.city.height,
        )

        # Calcular offset para centrar mapa
        map_width = self.city.width * tile_size
        offset_x = (self.screen.get_width() - map_width) // 2
        offset_y = 10

        x, y = self.player.position
        center_x = offset_x + x * tile_size + tile_size // 2
        center_y = offset_y + y * tile_size + tile_size // 2

        if self.player.state == PlayerState.EXHAUSTED:
            color = self.colors["RED"]
        elif self.player.state == PlayerState.TIRED:
            color = self.colors["ORANGE"]
        else:
            color = self.colors["PURPLE"]  # Color Fase 2

        pygame.draw.circle(self.screen, color, (center_x, center_y), tile_size // 1.9)
        # Borde blanco para mayor visibilidad
        pygame.draw.circle(
            self.screen, self.colors["WHITE"], (center_x, center_y), tile_size // 4, 2
        )

    def _render_extended_ui(self):
        """UI extendida optimizada para ventana más pequeña"""
        font = pygame.font.Font(None, 20)  # Fuente más pequeña
        available_height = self.screen.get_height() - 150
        ui_y_start = available_height + 20  # Justo debajo del mapa

        # Información básica en columnas para aprovechar espacio horizontal
        col1_x = 10
        col2_x = 200
        col3_x = 400
        col4_x = 600

        # Columna 1: Estado del jugador
        stamina_text = f"Resistencia: {self.player.stamina:.0f}/100"
        text_surface = font.render(stamina_text, True, self.colors["WHITE"])
        self.screen.blit(text_surface, (col1_x, ui_y_start))

        # Barra de resistencia más pequeña
        bar_width = 100
        bar_height = 8
        bar_x = col1_x
        bar_y = ui_y_start + 15

        pygame.draw.rect(
            self.screen, self.colors["GRAY"], (bar_x, bar_y, bar_width, bar_height)
        )

        stamina_ratio = self.player.stamina / 100.0
        stamina_color = (
            self.colors["GREEN"]
            if stamina_ratio > 0.5
            else self.colors["YELLOW"] if stamina_ratio > 0.2 else self.colors["RED"]
        )

        pygame.draw.rect(
            self.screen,
            stamina_color,
            (bar_x, bar_y, bar_width * stamina_ratio, bar_height),
        )

        # Columna 2: Inventario
        inventory_text = f"Inventario: {self.inventory.get_count()}"
        text_surface = font.render(inventory_text, True, self.colors["WHITE"])
        self.screen.blit(text_surface, (col2_x, ui_y_start))

        weight_text = f"Peso: {self.inventory.current_weight:.1f}kg"
        text_surface = font.render(weight_text, True, self.colors["WHITE"])
        self.screen.blit(text_surface, (col2_x, ui_y_start + 15))

        # Columna 3: Pedido actual
        current_order = self.inventory.get_current_order()
        if current_order:
            current_text = f"Actual: {current_order.id}"
            color = (
                self.colors["YELLOW"]
                if current_order.state == OrderState.ACCEPTED
                else (
                    self.colors["GREEN"]
                    if current_order.state == OrderState.PICKED_UP
                    else self.colors["WHITE"]
                )
            )
            text_surface = font.render(current_text, True, color)
            self.screen.blit(text_surface, (col3_x, ui_y_start))

            payout_text = f"${current_order.payout}"
            text_surface = font.render(payout_text, True, color)
            self.screen.blit(text_surface, (col3_x, ui_y_start + 15))

        # Columna 4: Tiempo e ingresos
        time_left = max(0, self.game_duration - self.current_time)
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        time_text = f"Tiempo: {minutes:02d}:{seconds:02d}"
        text_surface = font.render(time_text, True, self.colors["WHITE"])
        self.screen.blit(text_surface, (col4_x, ui_y_start))

        earnings_text = f"${self.player.total_earnings}/${self.city.goal}"
        text_surface = font.render(earnings_text, True, self.colors["WHITE"])
        self.screen.blit(text_surface, (col4_x, ui_y_start + 15))
        # Mostrar clima actual en la HUD (columna 4)
        cond, inten, in_trans = self.weather_manager.get_ui_tuple()
        wx_text = f"Clima: {cond} ({inten:.2f})" + (" *" if in_trans else "")
        text_surface = font.render(wx_text, True, self.colors["WHITE"])
        self.screen.blit(text_surface, (col4_x, ui_y_start + 30))


        # Segunda fila: Estadísticas y controles
        row2_y = ui_y_start + 35

        # Estadísticas de pedidos
        stats = self.order_manager.get_statistics()
        stats_text = (
            f"Disponibles:{stats['available']} Completados:{stats['completed']}"
        )
        text_surface = font.render(stats_text, True, self.colors["WHITE"])
        self.screen.blit(text_surface, (col1_x, row2_y))

        # Sistema de deshacer
        undo_count = self.state_manager.get_undo_count()
        undo_text = f"Deshacer: {undo_count}"
        text_surface = font.render(undo_text, True, self.colors["BLUE"])
        self.screen.blit(text_surface, (col2_x, row2_y))

        # Recuperación
        current_time = time.time()
        time_since_movement = current_time - self.last_movement_time

        if time_since_movement > self.movement_cooldown:
            recovery_text = "Recuperando +2/s"
            text_surface = font.render(recovery_text, True, self.colors["PURPLE"])
            self.screen.blit(text_surface, (col3_x, row2_y))

        # Tercera fila: Controles compactos
        row3_y = ui_y_start + 50
        controls_font = pygame.font.Font(None, 20)
        controls_text = "ESPACIO = Pedidos // I = Ordenar // U = Deshacer // N/P = Navegar // C = Cancelar // ESC = Pausa // E = Aceptar/Recoger"
        text_surface = controls_font.render(controls_text, True, self.colors["BLACK"])
        self.screen.blit(text_surface, (col1_x, row3_y))

    def _render_order_selection(self):
        """Renderiza menú de selección de pedidos"""
        # Overlay semi-transparente
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        overlay.fill(self.colors["BLACK"])
        overlay.set_alpha(200)
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.Font(None, 36)
        title_text = font.render("Seleccionar Pedido", True, self.colors["WHITE"])
        title_rect = title_text.get_rect(center=(self.screen.get_width() // 2, 50))
        self.screen.blit(title_text, title_rect)

        # Mostrar modo de ordenamiento actual
        sort_font = pygame.font.Font(None, 24)
        sort_text = f"Orden actual: {self.inventory_sort_mode.upper()}"
        sort_rect = sort_font.render(sort_text, True, self.colors["CYAN"]).get_rect(
            center=(self.screen.get_width() // 2, 80)
        )
        self.screen.blit(
            sort_font.render(sort_text, True, self.colors["CYAN"]), sort_rect
        )

        # Obtener pedidos disponibles ordenados según el modo actual
        available_orders = self._get_sorted_available_orders()

        if not available_orders:
            font = pygame.font.Font(None, 24)
            no_orders_text = font.render(
                "No hay pedidos disponibles", True, self.colors["GRAY"]
            )
            no_orders_rect = no_orders_text.get_rect(
                center=(self.screen.get_width() // 2, 200)
            )
            self.screen.blit(no_orders_text, no_orders_rect)
        else:
            # Mostrar lista de pedidos
            font = pygame.font.Font(None, 24)
            start_y = 100

            # Obtener lista de pedidos en inventario para marcar [ACEPTADO]/[CURRENT]
            inventory_list = self.inventory.orders.to_list()
            current_order = self.inventory.get_current_order()

            for i, order in enumerate(available_orders[:10]):  # Mostrar máximo 10
                # Determinar color basado en si está seleccionado
                if i == self.selected_order_index:
                    color = self.colors["YELLOW"]
                    # Dibujar rectángulo de selección
                    selection_rect = pygame.Rect(
                        50, start_y + i * 35 - 2, self.screen.get_width() - 100, 30
                    )
                    pygame.draw.rect(
                        self.screen, self.colors["DARK_GREEN"], selection_rect
                    )
                else:
                    color = self.colors["WHITE"]

                # Determinar estado/etiqueta
                status = ""
                # Si el pedido está en inventario (aceptado)
                if order.id in [o.id for o in inventory_list]:
                    if current_order and order.id == current_order.id:
                        status = " [CURRENT]"
                    else:
                        status = " [ACEPTADO]"

                # Información del pedido
                order_info = (
                    f"{order.id} - Prioridad: {order.priority} - "
                    f"Peso: {order.weight}kg - Pago: ${order.payout}{status}"
                )

                text_surface = font.render(order_info, True, color)
                self.screen.blit(text_surface, (60, start_y + i * 35))

                # Mostrar si se puede aceptar
                if not self.inventory.can_add_order(order) or any(
                    o.state in [OrderState.ACCEPTED, OrderState.PICKED_UP]
                    for o in self.order_manager.all_orders.values()
                ):
                    # Si ya hay un pedido activo global o no hay capacidad, avisar
                    warning_text = font.render(
                        "(No disponible ahora)", True, self.colors["RED"]
                    )
                    self.screen.blit(warning_text, (500, start_y + i * 35))

        # Controles
        font = pygame.font.Font(None, 20)
        controls = [
            "↑/↓ - Navegar | ENTER - Aceptar | ESC - Cancelar",
            "1 - Ordenar por prioridad | 2 - Por deadline | 3 - Por pago",
        ]

        for i, control in enumerate(controls):
            text_surface = font.render(control, True, self.colors["GRAY"])
            control_rect = text_surface.get_rect(
                center=(
                    self.screen.get_width() // 2,
                    self.screen.get_height() - 60 + i * 20,
                )
            )
            self.screen.blit(text_surface, control_rect)

    def _render_pause_overlay(self):
        """Renderiza overlay de pausa"""
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        overlay.fill(self.colors["BLACK"])
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.Font(None, 48)
        pause_text = font.render("PAUSADO", True, self.colors["WHITE"])
        pause_rect = pause_text.get_rect(
            center=(self.screen.get_width() // 2, self.screen.get_height() // 2 - 50)
        )
        self.screen.blit(pause_text, pause_rect)

        font = pygame.font.Font(None, 24)
        continue_text = font.render(
            "ESC - Continuar | Q - Salir", True, self.colors["WHITE"]
        )
        continue_rect = continue_text.get_rect(
            center=(self.screen.get_width() // 2, self.screen.get_height() // 2 + 20)
        )
        self.screen.blit(continue_text, continue_rect)

    def _render_game_end(self):
        """Renderiza pantalla de fin de juego con puntuación"""
        self.screen.fill(self.colors["BLACK"])

        font = pygame.font.Font(None, 48)
        if self.state == GameState.VICTORY:
            end_text = font.render("¡VICTORIA!", True, self.colors["GREEN"])
        else:
            end_text = font.render("DERROTA", True, self.colors["RED"])

        end_rect = end_text.get_rect(center=(self.screen.get_width() // 2, 100))
        self.screen.blit(end_text, end_rect)

        # Calcular y mostrar puntuación final
        stats = self.order_manager.get_statistics()
        score_data = self.score_calculator.calculate_final_score(
            total_earnings=self.player.total_earnings,
            reputation_multiplier=1.0,  # Será implementado en Fase 4
            completion_time=self.current_time,
            total_game_time=self.game_duration,
            cancelled_orders=stats.get("cancelled", 0),
            expired_orders=stats.get("expired", 0),
            late_deliveries=0,  # Será implementado en Fase 4
        )

        font = pygame.font.Font(None, 24)
        y_offset = 180

        score_info = [
            f"Ingresos totales: ${score_data['breakdown']['earnings']}",
            f"Puntuación base: {score_data['base_score']:.0f}",
            f"Bonus tiempo: {score_data['time_bonus']:.0f}",
            f"Penalizaciones: -{score_data['penalties']:.0f}",
            f"PUNTUACIÓN FINAL: {score_data['final_score']:.0f}",
            "",
            f"Pedidos completados: {stats['completed']}",
            f"Pedidos cancelados: {stats.get('cancelled', 0)}",
            f"Pedidos expirados: {stats.get('expired', 0)}",
        ]

        for i, info in enumerate(score_info):
            if info == "":
                continue

            color = self.colors["YELLOW"] if "FINAL" in info else self.colors["WHITE"]
            text_surface = font.render(info, True, color)
            text_rect = text_surface.get_rect(
                center=(self.screen.get_width() // 2, y_offset + i * 25)
            )
            self.screen.blit(text_surface, text_rect)

        # Controles
        font = pygame.font.Font(None, 20)
        controls_text = "ESPACIO - Volver al menú | Q/ESC - Salir"
        text_surface = font.render(controls_text, True, self.colors["GRAY"])
        controls_rect = text_surface.get_rect(
            center=(self.screen.get_width() // 2, self.screen.get_height() - 50)
        )
        self.screen.blit(text_surface, controls_rect)

    def load_city_data(self, city_data: Dict[str, Any]) -> bool:
        """Carga datos de la ciudad"""
        return self.city.load_from_dict(city_data)

    def load_orders_data(self, orders_data: List[Dict[str, Any]]):
        """Carga datos de pedidos"""
        self.order_manager.load_orders(orders_data)

    def run(self):
        """Bucle principal del juego"""
        while self.running:
            delta_time = self.clock.tick(self.fps) / 1000.0

            self.handle_events()
            self.update(delta_time)
            self.render()

        pygame.quit()

    def _fetch_resource(
    self,
    api_call,                 # función que retorna el payload o None
    cache_key: str,           # "city" | "orders" | "weather"
    file_name: str,           # "city.json" | "orders.json" | "weather.json"
    expect_list: bool = False,# True si esperas lista (orders)
    cache_ttl: int = 60*5     # edad máxima del cache, por si la red falla
    ) -> Optional[Tuple[Optional[Any], str]]:
        """
        Intenta SIEMPRE API primero. Si hay respuesta:
        - actualiza caché y archivo
        - retorna los datos
        Si falla API:
        - intenta caché (dentro de TTL)
        - intenta archivo local
        Si todo falla: retorna None
        """
        # 1) API primero
        data = api_call()
        if data is not None:
            # Normalización defensiva por si viene envuelto
            if expect_list and isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    data = data["data"]
                elif "orders" in data and isinstance(data["orders"], list):
                    data = data["orders"]

            # Guardar caché + archivo SIEMPRE que el API respondió
            ts = datetime.now().timestamp()
            self.cache_manager.save_cache(cache_key, data, ts)
            # Para orders guardamos dentro de {"orders": ...} como ya hacías
            file_payload = {"orders": data} if cache_key == "orders" else data
            self.file_manager.save_json(file_payload, file_name)

            source = "API"
            return data, source

        # 2) Fallback a caché
        cached = self.cache_manager.load_cache(cache_key, cache_ttl)
        if cached is not None:
            source = "cache"
            # Si es orders y lo quisiste guardar como lista plana en cache, úsalo tal cual
            return cached, source

        # 3) Fallback a archivo local
        file_json = self.file_manager.load_json(file_name)
        if file_json is not None:
            if expect_list and isinstance(file_json, dict) and "orders" in file_json:
                file_json = file_json["orders"]
            source = "file"
            return file_json, source

        return None, "none"


    def refresh_city(self) -> bool:
        city_data, src = self._fetch_resource(
            api_call=self.api_manager.get_city,
            cache_key="city",
            file_name="city.json",
            expect_list=False,
            cache_ttl=60*5
        )
        if not city_data:
            print("No se pudo cargar datos de ciudad (API/cache/file).")
            return False
        print(f"Ciudad cargada desde {src}.")
        if not self.load_city_data(city_data):
            print("Error cargando mapa: formato incorrecto.")
            return False
        return True


    def refresh_orders(self) -> bool:
        orders_data, src = self._fetch_resource(
            api_call=self.api_manager.get_orders,
            cache_key="orders",
            file_name="orders.json",
            expect_list=True,
            cache_ttl=60*5
        )
        if not orders_data:
            print("No se pudo cargar datos de pedidos (API/cache/file).")
            return False
        if not isinstance(orders_data, list):
            print("Error: orders_data no es una lista.")
            return False
        print(f"Pedidos cargados desde {src}.")
        self.load_orders_data(orders_data)
        # repoblar cola de prioridad a t=0 por si nos actualizamos en menú
        self.order_manager.update_available_orders(0.0)
        return True


    def load_data_phase3(self):
        """Carga datos con política API-first (actualiza memoria + cache + archivo)."""
        if not self.refresh_city():
            return False
        if not self.refresh_orders():
            return False
        return True

    def save_game(self, filename="savegame.dat"):
            """Guarda el estado actual de la partida"""
            game_state = {
                "player": deepcopy(self.player.__dict__),
                "inventory": [order.id for order in self.inventory.orders.to_list()],
                "orders": {
                    oid: order.__dict__
                    for oid, order in self.order_manager.all_orders.items()
                },
                "current_time": self.current_time,
            }
            self.file_manager.save_game(game_state, filename)
            print(f"Partida guardada en {filename}")

    def load_game(self, filename="savegame.dat"):
            """Carga una partida guardada"""
            game_state = self.file_manager.load_game(filename)
            if not game_state:
                print("No se pudo cargar la partida.")
                return False
            # Restaurar player
            for k, v in game_state["player"].items():
                setattr(self.player, k, v)
            # Restaurar pedidos
            for oid, odata in game_state["orders"].items():
                if oid in self.order_manager.all_orders:
                    for k, v in odata.items():
                        setattr(self.order_manager.all_orders[oid], k, v)
            # Restaurar inventario
            self.inventory.orders = DoublyLinkedList()
            self.inventory.orders_by_id.clear()
            self.inventory.current_weight = 0.0
            for oid in game_state["inventory"]:
                order = self.order_manager.all_orders.get(oid)
                if order:
                    self.inventory.add_order(order)
            self.current_time = game_state["current_time"]
            print(f"Partida cargada desde {filename}")
            return True

    def save_score(self, player_name: str, score: int):
            scores = self.file_manager.load_scores()
            scores.append({"name": player_name, "score": score})
            self.file_manager.save_scores(scores)
            print("Puntaje guardado.")

    def show_scores(self):
            scores = self.file_manager.load_scores()
            print("Tabla de puntajes:")
            for idx, entry in enumerate(scores, 1):
                print(f"{idx}. {entry['name']}: {entry['score']}")

    def refresh_weather(self) -> bool:
        # intenta API -> cache -> archivo local
        weather_cfg, src = self._fetch_resource(
            api_call=getattr(self.api_manager, "get_weather", lambda: None),
            cache_key="weather",
            file_name="weather.json",
            expect_list=False,
            cache_ttl=60*5,
        )

        if not weather_cfg:
            # Fallback: JSON por defecto (TigerCity)
            weather_cfg = {
                "version": "1.2",
                "data": {
                    "initial": {"condition": "clear", "intensity": 0.1},
                    "conditions": [
                        "clear","clouds","rain_light","rain","storm","fog","wind","heat","cold"
                    ],
                    "transition": {
                        "clear":  {"clear":0.2,"clouds":0.2,"wind":0.2,"heat":0.2,"cold":0.2},
                        "clouds": {"clear":0.2,"clouds":0.2,"rain_light":0.2,"wind":0.2,"fog":0.2},
                        "rain_light":{"clouds":0.333,"rain_light":0.333,"rain":0.333},
                        "rain":   {"rain_light":0.25,"rain":0.25,"storm":0.25,"clouds":0.25},
                        "storm":  {"rain":0.5,"clouds":0.5},
                        "fog":    {"clouds":0.333,"fog":0.333,"clear":0.333},
                        "wind":   {"wind":0.333,"clouds":0.333,"clear":0.333},
                        "heat":   {"heat":0.333,"clear":0.333,"clouds":0.333},
                        "cold":   {"cold":0.333,"clear":0.333,"clouds":0.333},
                    },
                }
            }
            src = "default"  # <<< marca que usamos el fallback del código

        # Inicializa el manager y LOGUEA la fuente
        self.weather_manager.init_from_api_config(weather_cfg)
        print(f"Clima cargado desde {src}.")
        return True


    # def refresh_weather(self) -> bool:
    #     # intenta API -> cache -> archivo local
    #     weather_cfg, src = self._fetch_resource(
    #         api_call=getattr(self.api_manager, "get_weather", lambda: None),
    #         cache_key="weather",
    #         file_name="weather.json",
    #         expect_list=False,
    #         cache_ttl=60*5,
    #     )

    #     if not weather_cfg:
    #         # Fallback: JSON por defecto (tu esquema TigerCity)
    #         weather_cfg = {
    #             "version": "1.2",
    #             "data": {
    #                 "initial": {"condition": "clear", "intensity": 0.1},
    #                 "conditions": [
    #                     "clear","clouds","rain_light","rain","storm","fog","wind","heat","cold"
    #                 ],
    #                 "transition": {
    #                     "clear":  {"clear":0.2,"clouds":0.2,"wind":0.2,"heat":0.2,"cold":0.2},
    #                     "clouds": {"clear":0.2,"clouds":0.2,"rain_light":0.2,"wind":0.2,"fog":0.2},
    #                     "rain_light":{"clouds":0.333,"rain_light":0.333,"rain":0.333},
    #                     "rain":   {"rain_light":0.25,"rain":0.25,"storm":0.25,"clouds":0.25},
    #                     "storm":  {"rain":0.5,"clouds":0.5},
    #                     "fog":    {"clouds":0.333,"fog":0.333,"clear":0.333},
    #                     "wind":   {"wind":0.333,"clouds":0.333,"clear":0.333},
    #                     "heat":   {"heat":0.333,"clear":0.333,"clouds":0.333},
    #                     "cold":   {"cold":0.333,"clear":0.333,"clouds":0.333},
    #                 },
    #             }
    #         }

    #     # CORREGIDO: usar el manager correcto
    #     self.weather_manager.init_from_api_config(weather_cfg)
    #     print("Clima inicializado.")
    #     return True
