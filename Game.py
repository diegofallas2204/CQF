import inspect
import os
import time
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pygame

from DataStructure.DoublyLinkedList import DoublyLinkedList
from Entities.City import City
from Entities.Player import Player
from Management.APIManager import APIManager
from Management.CacheManager import CacheManager
from Management.FileManager import FileManager
from Management.GameStateManager import GameStateManager
from Management.Inventory import Inventory
from Management.OrderManager import OrderManager
from Management.ScoreCalculator import ScoreCalculator
from Management.WeatherManager import WeatherManager
from State.GameState import GameState
from State.OrderState import OrderState
from State.PlayerState import PlayerState


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
        self.hud_reserved = 160
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
        self.late_deliveries = 0
        # ---- Punto 9: puntaje final y tablero ----
        self._game_end_reason = None  # "victory" | "timeout" | "reputation"
        self._final_score_data = None  # cache del cálculo para render
        self._score_saved = False  # evitar guardar dos veces
        self.player_name = "Player"  # simple; si quieres, luego implementamos input

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
        # Guardar (F5)
        elif key == pygame.K_F5:
            self.save_game_quick("quick.sav")

        # Cargar (F9)
        elif key == pygame.K_F9:
            self.load_game_quick("quick.sav")

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
            # Guardar (F5)
        elif key == pygame.K_F5:
            self.save_game_quick("quick.sav")

        # Cargar (F9)
        elif key == pygame.K_F9:
            self.load_game_quick("quick.sav")

    def _handle_game_end_input(self, key):
        """Manejo de input en fin de juego"""
        if key == pygame.K_SPACE:
            self.state = GameState.MENU
            self._reset_game()
        elif key in [pygame.K_q, pygame.K_ESCAPE]:
            self.running = False
        elif key == pygame.K_s:
            if not self._score_saved and self._final_score_data:
                self.save_score(
                    self.player_name, int(self._final_score_data["final_score"])
                )
                self._score_saved = True
                print("Puntaje guardado.")

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
        """Entrega el pedido actual con ajuste de reputación y pago."""
        current_order = self.inventory.get_current_order()
        if not current_order:
            return

        delivered_order = self.order_manager.deliver_order(current_order.id)
        if not delivered_order:
            return

        # Determinar puntualidad
        # Si Order.deliver_order ya puso delivery_time = now, úsalo:
        delivery_time = delivered_order.delivery_time
        delay_seconds = delivered_order.calculate_delay(delivery_time)
        early = delivered_order.is_early_delivery(delivery_time)

        # Ajuste de reputación segun resultado (Punto 7)
        rep_delta = self.player.register_delivery_outcome(
            delay_seconds=delay_seconds,
            early=early,
        )
        # Contador de tardanzas para puntaje (solo si tardó)
        if delay_seconds > 0:
            self.late_deliveries += 1

        # Multiplicador de pago por reputación (≥90 → +5%)
        pay_mult = self.player.get_pay_multiplier()
        payout = int(round(delivered_order.payout * pay_mult))
        self.player.add_earnings(payout)

        # Remover del inventario y sincronizar peso
        self.inventory.remove_order(delivered_order.id)
        self.player.inventory_weight = self.inventory.current_weight

        print(
            f"¡Pedido {delivered_order.id} entregado! Pago ${payout} (mult x{pay_mult:.2f})"
        )
        if rep_delta != 0:
            print(
                f"Reputación ajustada: {('+' if rep_delta>0 else '')}{rep_delta} → {self.player.reputation}"
            )
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

            # Penalización de reputación (PDF: -4) — sin quitar dinero directo
            penalty_rep = -4
            self.player.apply_reputation_change(penalty_rep)

            print(f"Pedido {current_order.id} cancelado. {penalty_rep} reputación.")
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

        # ---- Punto 9: reset métricas/flags
        self.late_deliveries = 0
        self._game_end_reason = None
        self._final_score_data = None
        self._score_saved = False
        # Punto 7: reset de “primera tardanza con rep alta”
        if hasattr(self.player, "_first_late_discount_used"):
            self.player._first_late_discount_used = False

        # Actualizar pedidos disponibles a t=0 (release_time)
        self.order_manager.update_available_orders(0.0)

        # Inicializar configuración de clima (API/cache/file o fallback)
        self.refresh_weather()

        # --- DEBUG: acelerar clima para pruebas ---
        try:
            self.weather_manager._rand_burst = lambda: 12  # cada ~12 s
            self.weather_manager._rand_transition = lambda: 2
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

        # Sincronizar peso del jugador con el inventario
        self.player.inventory_weight = self.inventory.current_weight

        # Abrir directamente el menú de selección de pedidos
        self.state = GameState.ORDER_SELECTION
        self.selected_order_index = 0
        print("Menú de pedidos abierto automáticamente")

        # ↓↓↓ SOLO PARA PRUEBA DE VICTORIA ↓↓↓
        # self.city.goal = 180
        print(f"[DEBUG] Meta de ingresos forzada a ${self.city.goal}")
        # ↑↑↑ BORRAR/COMENTAR PARA ENTREGA ↑↑↑

    def _reset_game(self):
        """Resetea el juego para nueva partida"""
        self.player = Player()
        self.inventory = Inventory()
        self.state_manager.clear_history()

        self.selected_order_index = 0
        self.inventory_sort_mode = "priority"

        # ---- Punto 9: reset banderas/métricas
        self._game_end_reason = None
        self._final_score_data = None
        self._score_saved = False
        self.late_deliveries = 0

        # Punto 7: reset de “primera tardanza con rep alta”
        if hasattr(self.player, "_first_late_discount_used"):
            self.player._first_late_discount_used = False

    def update(self, delta_time: float):
        """Actualización extendida del juego"""
        if self.state == GameState.PLAYING:
            self.current_time = time.time() - self.game_start_time

            # Actualizar pedidos disponibles y expirados
            self.order_manager.update_available_orders(self.current_time)
            # Expiraciones: penalización reputación y limpieza de inventario
            just_expired = self.order_manager.update_expired_orders()
            for o in just_expired:
                # -6 reputación (PDF)
                self.player.apply_reputation_change(-6)
                # si estaba en inventario → remover
                self.inventory.remove_order(o.id)
                self.player.inventory_weight = self.inventory.current_weight
                print(
                    f"Pedido {o.id} expiró. -6 reputación. Rep={self.player.reputation}"
                )

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
        # Victoria por ingresos
        if self.player.total_earnings >= self.city.goal:
            self.state = GameState.VICTORY
            self._game_end_reason = "victory"
            self._compute_final_score_once()
            return

        # Derrota por reputación
        if getattr(self.player, "reputation", 100) < 20:
            self.state = GameState.GAME_OVER
            self._game_end_reason = "reputation"
            self._compute_final_score_once()
            return

        # Derrota por tiempo
        if self.current_time >= self.game_duration:
            self.state = GameState.GAME_OVER
            self._game_end_reason = "timeout"
            self._compute_final_score_once()
            return

    def render(self):
        """Renderizado extendido"""
        # Fondo según clima
        bg = (
            self.weather_manager.get_background_color()
            if self.weather_manager
            else self.colors["BLACK"]
        )
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
        if getattr(self, "_toast_text", None) and time.time() < getattr(
            self, "_toast_until", 0
        ):
            f = pygame.font.Font(None, 28)
            surf = f.render(self._toast_text, True, self.colors["WHITE"])
            pad = 10
            box = pygame.Surface(
                (surf.get_width() + 2 * pad, surf.get_height() + 2 * pad),
                pygame.SRCALPHA,
            )
            pygame.draw.rect(box, (0, 0, 0, 180), box.get_rect(), border_radius=8)
            box.blit(surf, (pad, pad))
            # esquina inferior derecha
            x = self.screen.get_width() - box.get_width() - 12
            y = (
                self.screen.get_height() - box.get_height() - 12 - 140
            )  # deja despejada tu HUD
            self.screen.blit(box, (x, y))

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

    def _tile_geom(self):
        """
        Devuelve (tile_size, offset_x, offset_y) calculados de forma consistente
        para **todas** las funciones que dibujan el mapa, jugador y pedidos.
        """
        if not self.city.tiles:
            return (0, 0, 0)

        available_height = self.screen.get_height() - self.hud_reserved
        tile_size = min(
            self.screen.get_width() // self.city.width,
            available_height // self.city.height,
        )

        map_width = self.city.width * tile_size
        map_height = self.city.height * tile_size
        offset_x = (self.screen.get_width() - map_width) // 2
        offset_y = 10  # margen superior constante

        return (tile_size, offset_x, offset_y)

    def _render_map(self):
        if not self.city.tiles:
            return

        tile_size, offset_x, offset_y = self._tile_geom()
        if tile_size <= 0:
            return

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
        if not self.city.tiles:
            return

        tile_size, offset_x, offset_y = self._tile_geom()
        if tile_size <= 0:
            return

        icon_radius = max(6, tile_size // 4)
        font = pygame.font.Font(None, max(14, tile_size // 3))

        current_game_time = self.current_time

        # Pickups de pedidos AVAILABLE cuyo release_time ya pasó
        for order in self.order_manager.all_orders.values():
            if (
                order.state == OrderState.AVAILABLE
                and current_game_time >= order.release_time
            ):
                px, py = order.pickup
                cx = offset_x + px * tile_size + tile_size // 2
                cy = offset_y + py * tile_size + tile_size // 2

                pygame.draw.circle(
                    self.screen, self.colors["BLUE"], (cx, cy), icon_radius
                )
                pygame.draw.circle(
                    self.screen, self.colors["WHITE"], (cx, cy), icon_radius, 2
                )
                text = font.render("P", True, self.colors["WHITE"])
                self.screen.blit(text, text.get_rect(center=(cx, cy)))

        # Dropoff del pedido actual
        current_order = self.inventory.get_current_order()
        if current_order and current_order.state in [
            OrderState.ACCEPTED,
            OrderState.PICKED_UP,
        ]:
            dx, dy = current_order.dropoff
            cx = offset_x + dx * tile_size + tile_size // 2
            cy = offset_y + dy * tile_size + tile_size // 2
            pygame.draw.circle(self.screen, self.colors["RED"], (cx, cy), icon_radius)
            pygame.draw.circle(
                self.screen, self.colors["WHITE"], (cx, cy), icon_radius, 2
            )
            text = font.render("D", True, self.colors["WHITE"])
            self.screen.blit(text, text.get_rect(center=(cx, cy)))

            if current_order.state == OrderState.PICKED_UP:
                pxc = offset_x + current_order.pickup[0] * tile_size + tile_size // 2
                pyc = offset_y + current_order.pickup[1] * tile_size + tile_size // 2
                pygame.draw.line(
                    self.screen, self.colors["YELLOW"], (pxc, pyc), (cx, cy), 3
                )

    def _render_player(self):
        if not self.city.tiles:
            return

        tile_size, offset_x, offset_y = self._tile_geom()
        if tile_size <= 0:
            return

        x, y = self.player.position
        cx = offset_x + x * tile_size + tile_size // 2
        cy = offset_y + y * tile_size + tile_size // 2

        if self.player.state == PlayerState.EXHAUSTED:
            color = self.colors["RED"]
        elif self.player.state == PlayerState.TIRED:
            color = self.colors["ORANGE"]
        else:
            color = self.colors["PURPLE"]

        pygame.draw.circle(self.screen, color, (cx, cy), tile_size // 1.9)
        pygame.draw.circle(
            self.screen, self.colors["WHITE"], (cx, cy), tile_size // 4, 2
        )

    # ---------- Helpers UI ----------
    def _draw_text(self, text, x, y, color, size=22, *, center=False, shadow=True):
        """Dibuja texto con sombra sutil para mejorar contraste."""
        font = pygame.font.Font(None, size)
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)

        if shadow:
            shadow_surf = font.render(text, True, (0, 0, 0))
            shadow_rect = shadow_surf.get_rect()
            shadow_rect.topleft = (rect.left + 1, rect.top + 1)
            self.screen.blit(shadow_surf, shadow_rect)

        self.screen.blit(surf, rect)
        return rect

    def _draw_panel(self, x, y, w, h, *, alpha=180, radius=10, color=(20, 40, 60)):
        """Dibuja un panel translúcido con borde redondeado."""
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        r, g, b = color
        panel.fill((0, 0, 0, 0))
        pygame.draw.rect(
            panel, (r, g, b, alpha), panel.get_rect(), border_radius=radius
        )
        self.screen.blit(panel, (x, y))

    def _render_extended_ui(self):
        """HUD con panel translúcido, columnas y tipografía más legible."""
        # --- Layout base ---
        panel_margin_x = 8
        panel_margin_y = 6

        available_height = self.screen.get_height() - self.hud_reserved
        ui_y_start = available_height + 8

        panel_x = 6
        panel_y = ui_y_start - 6
        panel_w = self.screen.get_width() - 12
        panel_h = 140  # altura del panel HUD

        # Panel translúcido (contraste con el fondo/clima)
        self._draw_panel(
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            alpha=170,
            radius=12,
            color=(25, 70, 100),
        )

        # Columnas (4)
        col_w = panel_w // 4
        col_x = [panel_x + panel_margin_x + col_w * i for i in range(4)]
        row_y1 = panel_y + panel_margin_y + 6
        row_y2 = row_y1 + 22
        row_y3 = row_y2 + 22
        row_y4 = row_y3 + 22  # fila extra

        # ------ Columna 1: Player ------
        self._draw_text(
            f"Resistencia: {self.player.stamina:.0f}/100",
            col_x[0],
            row_y1,
            self.colors["WHITE"],
            size=22,
        )
        # Barra de resistencia
        bar_w, bar_h = 140, 10
        bar_x, bar_y = col_x[0], row_y1 + 18
        pygame.draw.rect(
            self.screen,
            self.colors["GRAY"],
            (bar_x, bar_y, bar_w, bar_h),
            border_radius=4,
        )
        stamina_ratio = max(0.0, min(1.0, self.player.stamina / 100.0))
        stamina_color = (
            self.colors["GREEN"]
            if stamina_ratio > 0.5
            else self.colors["YELLOW"] if stamina_ratio > 0.2 else self.colors["RED"]
        )
        pygame.draw.rect(
            self.screen,
            stamina_color,
            (bar_x, bar_y, int(bar_w * stamina_ratio), bar_h),
            border_radius=4,
        )

        # Reputación y multiplicador (bajadas 10 px para no chocar con la barra)
        self._draw_text(
            f"Reputación: {self.player.reputation}/100",
            col_x[0],
            row_y2 + 10,
            self.colors["WHITE"],
            size=20,
        )
        self._draw_text(
            f"Pago x{self.player.get_pay_multiplier():.2f}",
            col_x[0],
            row_y3 + 10,
            self.colors["YELLOW"],
            size=20,
        )

        # ------ Columna 2: Inventario ------
        self._draw_text(
            f"Inventario: {self.inventory.get_count()}",
            col_x[1],
            row_y1,
            self.colors["WHITE"],
            size=22,
        )
        self._draw_text(
            f"Peso: {self.inventory.current_weight:.1f}kg",
            col_x[1],
            row_y2,
            self.colors["WHITE"],
            size=20,
        )

        # Sistema de deshacer / stats
        undo_count = self.state_manager.get_undo_count()
        self._draw_text(
            f"Deshacer: {undo_count}", col_x[1], row_y3, self.colors["CYAN"], size=20
        )

        # ------ Columna 3: Pedido actual / recuperación ------
        current_order = self.inventory.get_current_order()
        if current_order:
            color = (
                self.colors["YELLOW"]
                if current_order.state == OrderState.ACCEPTED
                else (
                    self.colors["GREEN"]
                    if current_order.state == OrderState.PICKED_UP
                    else self.colors["WHITE"]
                )
            )
            self._draw_text(
                f"Actual: {current_order.id}", col_x[2], row_y1, color, size=22
            )
            self._draw_text(
                f"${current_order.payout}", col_x[2], row_y2, color, size=20
            )

        # Recuperación si está quieto
        current_time = time.time()
        if current_time - self.last_movement_time > self.movement_cooldown:
            self._draw_text(
                "Recuperando +2/s", col_x[2], row_y3, self.colors["PURPLE"], size=20
            )

        # ------ Columna 4: Tiempo / ingresos / clima ------
        time_left = max(0, self.game_duration - self.current_time)
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        self._draw_text(
            f"Tiempo: {minutes:02d}:{seconds:02d}",
            col_x[3],
            row_y1,
            self.colors["WHITE"],
            size=22,
        )
        self._draw_text(
            f"${self.player.total_earnings}/${self.city.goal}",
            col_x[3],
            row_y2,
            self.colors["WHITE"],
            size=20,
        )

        cond, inten, in_trans = self.weather_manager.get_ui_tuple()
        wx = f"Clima: {cond} ({inten:.2f})" + (" *" if in_trans else "")
        self._draw_text(wx, col_x[3], row_y3, self.colors["WHITE"], size=20)

        # ---------- Punto 9: Preview de score en vivo (columna derecha, bajo clima) ----------
        stats = self.order_manager.get_statistics()
        rep_mult = (
            self.player.get_pay_multiplier()
            if hasattr(self.player, "get_pay_multiplier")
            else 1.0
        )
        base_now = int(self.player.total_earnings * rep_mult)
        time_bonus_now = int(
            self.score_calculator.calculate_time_bonus(
                self.current_time, self.game_duration
            )
        )
        penalties_now = (
            stats.get("cancelled", 0) * 50
            + stats.get("expired", 0) * 100
            + self.late_deliveries * 25
        )
        final_now = max(0, base_now + time_bonus_now - penalties_now)

        preview_x = col_x[3]
        preview_y = row_y4  # usa la fila extra para evitar choques
        self._draw_text(
            f"Score (ahora): {final_now}",
            preview_x,
            preview_y,
            self.colors["YELLOW"],
            size=20,
        )
        self._draw_text(
            f"base={base_now}  bonus={time_bonus_now}  -{penalties_now}",
            preview_x,
            preview_y + 18,
            self.colors["WHITE"],
            size=16,
        )

        # ------ Fila extra izquierda: stats compactos ------
        self._draw_text(
            f"Disponibles:{stats['available']}  Completados:{stats['completed']}",
            panel_x + 12,
            row_y4,
            self.colors["WHITE"],
            size=18,
        )

        # ------ Controles (dos líneas si hace falta) ------
        controls = "ESPACIO = Pedidos  |  I = Ordenar  |  U = Deshacer  |  N/P = Navegar  |  C = Cancelar  |  ESC = Pausa  |  E = Aceptar/Recoger  |  F5 = Guardar Partida  |  F9 = Cargar Partida"
        max_width = panel_w - 24
        font = pygame.font.Font(None, 18)
        words = controls.split()
        lines, line = [], ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] <= max_width:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)

        controls_y = panel_y + panel_h - 18
        if len(lines) == 1:
            self._draw_text(
                lines[0],
                panel_x + 12,
                controls_y,
                self.colors["BLACK"],
                size=18,
                shadow=False,
            )
        else:
            self._draw_text(
                lines[0],
                panel_x + 12,
                controls_y - 16,
                self.colors["BLACK"],
                size=18,
                shadow=False,
            )
            self._draw_text(
                lines[1],
                panel_x + 12,
                controls_y,
                self.colors["BLACK"],
                size=18,
                shadow=False,
            )

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
            "ESC - Continuar | Q - Salir | F5 - Guardar Partida | F9 - Cargar Partida",
            True,
            self.colors["WHITE"],
        )
        continue_rect = continue_text.get_rect(
            center=(self.screen.get_width() // 2, self.screen.get_height() // 2 + 20)
        )
        self.screen.blit(continue_text, continue_rect)

    def _render_game_end(self):
        # Asegura cálculo cacheado
        self._compute_final_score_once()

        self.screen.fill(self.colors["BLACK"])
        font_title = pygame.font.Font(None, 48)
        font = pygame.font.Font(None, 28)

        # Título (Victoria/Derrota)
        is_victory = self._game_end_reason == "victory"
        title = "¡VICTORIA!" if is_victory else "DERROTA"
        title_color = self.colors["GREEN"] if is_victory else self.colors["RED"]
        self.screen.blit(
            font_title.render(title, True, title_color),
            (self.screen.get_width() // 2 - 100, 80),
        )

        # Motivo legible
        reason_map = {
            "victory": "Meta alcanzada",
            "timeout": "Se acabó el tiempo",
            "reputation": "Reputación muy baja",
        }
        motivo = reason_map.get(self._game_end_reason, "-")

        # Datos de score (defensivo si no hubiera sido calculado)
        sd = self._final_score_data or {}
        br = sd.get("breakdown", {})
        stats = self.order_manager.get_statistics()

        base_score = int(sd.get("base_score", 0))
        time_bonus = int(sd.get("time_bonus", 0))
        penalties = int(sd.get("penalties", 0))
        final_score = int(sd.get("final_score", 0))
        rep_mult = float(br.get("reputation_multiplier", 1.0))
        earnings = int(br.get("earnings", 0))

        y = 160
        # Motivo
        self.screen.blit(
            font.render(f"Motivo: {motivo}", True, self.colors["WHITE"]), (60, y)
        )
        y += 30
        # Ingresos y multiplicador
        self.screen.blit(
            font.render(f"Ingresos: ${earnings}", True, self.colors["WHITE"]), (60, y)
        )
        y += 30
        self.screen.blit(
            font.render(
                f"Multiplicador rep: x{rep_mult:.2f}", True, self.colors["WHITE"]
            ),
            (60, y),
        )
        y += 30
        # Desglose con colores útiles
        self.screen.blit(
            font.render(f"Puntuación base: {base_score}", True, self.colors["WHITE"]),
            (60, y),
        )
        y += 30
        self.screen.blit(
            font.render(f"Bonus tiempo: {time_bonus}", True, self.colors["GREEN"]),
            (60, y),
        )
        y += 30
        self.screen.blit(
            font.render(f"Penalizaciones: -{penalties}", True, self.colors["RED"]),
            (60, y),
        )
        y += 30

        # Puntaje final destacado
        final_color = self.colors["YELLOW"] if final_score > 0 else self.colors["GRAY"]
        self.screen.blit(
            font.render(f"PUNTUACIÓN FINAL: {final_score}", True, final_color), (60, y)
        )
        y += 36

        # Resumen de pedidos
        comp = stats.get("completed", 0)
        canc = stats.get("cancelled", 0)
        expi = stats.get("expired", 0)
        tard = getattr(self, "late_deliveries", 0)
        self.screen.blit(
            font.render(
                f"Completados: {comp}  Cancelados: {canc}  Expirados: {expi}  Tardanzas: {tard}",
                True,
                self.colors["WHITE"],
            ),
            (60, y),
        )
        y += 36

        # Instrucciones y estado de guardado
        self.screen.blit(
            font.render(
                "ESPACIO: Menú  |  Q/ESC: Salir  |  S: Guardar puntaje",
                True,
                self.colors["WHITE"],
            ),
            (60, y),
        )
        y += 30

        guardado_text = (
            "(ya guardado)" if self._score_saved else "(presiona S para guardar)"
        )
        self.screen.blit(font.render(guardado_text, True, self.colors["GRAY"]), (60, y))
        y += 24

        pygame.display.flip()

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
        api_call,  # función que retorna el payload o None
        cache_key: str,  # "city" | "orders" | "weather"
        file_name: str,  # "city.json" | "orders.json" | "weather.json"
        expect_list: bool = False,  # True si esperas lista (orders)
        cache_ttl: int = 60 * 5,  # edad máxima del cache, por si la red falla
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
            cache_ttl=60 * 5,
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
            cache_ttl=60 * 5,
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

    # ======== Guardado/Carga: helpers ========

    def _build_save_payload(self) -> dict:
        """Empaqueta el estado del juego usando solo tipos serializables."""
        # -- Orders: volcamos todos los campos necesarios para reconstruir
        orders_dump = []
        for o in self.order_manager.all_orders.values():
            orders_dump.append(
                {
                    "id": o.id,
                    "pickup": list(o.pickup),
                    "dropoff": list(o.dropoff),
                    "payout": int(o.payout),
                    "deadline": (
                        o.deadline.isoformat().replace("+00:00", "Z")
                        if hasattr(o.deadline, "isoformat")
                        else str(o.deadline)
                    ),
                    "weight": float(o.weight),
                    "priority": int(o.priority),
                    "release_time": float(o.release_time),
                    "state": str(
                        o.state.value if hasattr(o.state, "value") else o.state
                    ),
                }
            )

        # -- Inventario: sólo IDs
        inv_ids = [o.id for o in self.inventory.orders.to_list()]

        # -- Player snapshot
        player_dump = {
            "position": list(self.player.position),
            "stamina": float(self.player.stamina),
            "inventory_weight": float(self.player.inventory_weight),
            "total_earnings": int(self.player.total_earnings),
            "reputation": int(getattr(self.player, "reputation", 70)),
            # flags reputación (punto 7)
            "first_late_discount_used": bool(
                getattr(self.player, "_first_late_discount_used", False)
            ),
        }

        # -- Weather snapshot (mínimo necesario para reponer el aspecto/juego)
        cond, inten, in_trans = self.weather_manager.get_ui_tuple()
        weather_dump = {
            "condition": cond,
            "intensity": float(inten),
            "in_transition": bool(in_trans),
        }

        payload = {
            "version": 1,
            "timestamp": time.time(),
            "game": {
                "state": (
                    self.state.value
                    if hasattr(self.state, "value")
                    else str(self.state)
                ),
                "current_time": float(self.current_time),
                "game_duration": float(self.game_duration),
                "late_deliveries": int(getattr(self, "late_deliveries", 0)),
                "goal": int(self.city.goal),
                "player": player_dump,
                "inventory_ids": inv_ids,
                "orders": orders_dump,
                "weather": weather_dump,
            },
        }
        return payload

    def _apply_loaded_payload(self, payload: dict) -> bool:
        """Restaura el estado del juego desde un payload previamente guardado."""
        try:
            data = payload.get("game", {})
            # 1) City: mantenemos el mapa actual; solo ajustamos la meta
            self.city.goal = int(data.get("goal", self.city.goal))

            # 2) Orders: reconstruir y rehacer colas/listas
            orders_dump = data.get("orders", [])
            self.order_manager.load_orders(orders_dump)  # reutilizamos tu loader
            # Restaurar estados exactos
            from State.OrderState import OrderState as _OS

            for od in orders_dump:
                oid = od["id"]
                st = od.get("state", "available")
                if oid in self.order_manager.all_orders:
                    self.order_manager.all_orders[oid].state = _OS(st)

            # 3) Inventario: limpiar y reponer por IDs
            self.inventory.orders = DoublyLinkedList()
            self.inventory.orders_by_id.clear()
            self.inventory.current_weight = 0.0
            for oid in data.get("inventory_ids", []):
                if oid in self.order_manager.all_orders:
                    self.inventory.add_order(self.order_manager.all_orders[oid])

            # 4) Player
            pd = data.get("player", {})
            self.player.position = tuple(pd.get("position", self.player.position))
            self.player.stamina = float(pd.get("stamina", self.player.stamina))
            self.player.inventory_weight = float(
                pd.get("inventory_weight", self.inventory.current_weight)
            )
            self.player.total_earnings = int(
                pd.get("total_earnings", self.player.total_earnings)
            )
            if hasattr(self.player, "reputation"):
                self.player.reputation = int(
                    pd.get("reputation", self.player.reputation)
                )
            if hasattr(self.player, "_first_late_discount_used"):
                self.player._first_late_discount_used = bool(
                    pd.get("first_late_discount_used", False)
                )

            # 5) Tiempo de juego y métricas
            self.current_time = float(data.get("current_time", 0.0))
            self.game_duration = float(data.get("game_duration", self.game_duration))
            self.late_deliveries = int(data.get("late_deliveries", 0))

            # 6) Weather (reconstrucción mínima: reinit y fijar estado visible)
            #    Recargamos config (API/cache), luego pisamos el estado actual.
            self.refresh_weather()
            wd = data.get("weather", {})
            try:
                # fuerza estado visible
                self.weather_manager.current.condition = wd.get(
                    "condition", self.weather_manager.current.condition
                )
                self.weather_manager.current.intensity = float(
                    wd.get("intensity", self.weather_manager.current.intensity)
                )
                self.weather_manager.current.m_climate = self.weather_manager._mul_from(
                    self.weather_manager.current.condition,
                    self.weather_manager.current.intensity,
                )
                # cortar cualquier transición pendiente
                self.weather_manager.target = None
                self.weather_manager._trans_t = self.weather_manager._trans_dur = 0.0
            except Exception:
                pass

            # 7) Re-poblar cola de disponibles acorde al tiempo de juego
            self.order_manager.update_available_orders(self.current_time)

            # 8) Estado del juego tras cargar: te dejo en PAUSED para que el jugador decida
            from State.GameState import GameState as _GS

            self.state = _GS.PAUSED

            # 9) Limpiar flags de fin
            self._game_end_reason = None
            self._final_score_data = None
            self._score_saved = False

            # 10) Sincronizar peso
            self.player.inventory_weight = self.inventory.current_weight

            return True
        except Exception as e:
            print(f"[Load] Error aplicando save: {e}")
            return False

    def save_game_quick(self, filename: str = "quick.sav") -> bool:
        """Guarda la partida en /saves/quick.sav"""
        payload = self._build_save_payload()
        try:
            self.file_manager.save_game(payload, filename)
            self._toast("Partida guardada ✔")
            return True
        except Exception as e:
            print(f"[Save] Error: {e}")
            self._toast("Error al guardar ✖")
            return False

    def load_game_quick(self, filename: str = "quick.sav") -> bool:
        """Carga la partida desde /saves/quick.sav"""
        data = self.file_manager.load_game(filename)
        if not data:
            self._toast("No hay partida guardada")
            return False
        ok = self._apply_loaded_payload(data)
        self._toast("Partida cargada ✔" if ok else "Error al cargar ✖")
        return ok

    # (Opcional) mensajito overlay 1.5s
    def _toast(self, text: str, t: float = 1.5):
        self._toast_text = text
        self._toast_until = time.time() + t

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

    def _compute_final_score_once(self):
        """Calcula y cachea el puntaje final si aún no está calculado."""
        if self._final_score_data is not None:
            return
        stats = self.order_manager.get_statistics()
        rep_mult = (
            self.player.get_pay_multiplier()
            if hasattr(self.player, "get_pay_multiplier")
            else 1.0
        )
        self._final_score_data = self.score_calculator.calculate_final_score(
            total_earnings=self.player.total_earnings,
            reputation_multiplier=rep_mult,
            completion_time=self.current_time,
            total_game_time=self.game_duration,
            cancelled_orders=stats.get("cancelled", 0),
            expired_orders=stats.get("expired", 0),
            late_deliveries=self.late_deliveries,
        )
        # aún no se ha guardado en tabla
        self._score_saved = False

    def refresh_weather(self) -> bool:
        # intenta API -> cache -> archivo local
        weather_cfg, src = self._fetch_resource(
            api_call=getattr(self.api_manager, "get_weather", lambda: None),
            cache_key="weather",
            file_name="weather.json",
            expect_list=False,
            cache_ttl=60 * 5,
        )

        if not weather_cfg:
            # Fallback: JSON por defecto (TigerCity)
            weather_cfg = {
                "version": "1.2",
                "data": {
                    "initial": {"condition": "clear", "intensity": 0.1},
                    "conditions": [
                        "clear",
                        "clouds",
                        "rain_light",
                        "rain",
                        "storm",
                        "fog",
                        "wind",
                        "heat",
                        "cold",
                    ],
                    "transition": {
                        "clear": {
                            "clear": 0.2,
                            "clouds": 0.2,
                            "wind": 0.2,
                            "heat": 0.2,
                            "cold": 0.2,
                        },
                        "clouds": {
                            "clear": 0.2,
                            "clouds": 0.2,
                            "rain_light": 0.2,
                            "wind": 0.2,
                            "fog": 0.2,
                        },
                        "rain_light": {
                            "clouds": 0.333,
                            "rain_light": 0.333,
                            "rain": 0.333,
                        },
                        "rain": {
                            "rain_light": 0.25,
                            "rain": 0.25,
                            "storm": 0.25,
                            "clouds": 0.25,
                        },
                        "storm": {"rain": 0.5, "clouds": 0.5},
                        "fog": {"clouds": 0.333, "fog": 0.333, "clear": 0.333},
                        "wind": {"wind": 0.333, "clouds": 0.333, "clear": 0.333},
                        "heat": {"heat": 0.333, "clear": 0.333, "clouds": 0.333},
                        "cold": {"cold": 0.333, "clear": 0.333, "clouds": 0.333},
                    },
                },
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
