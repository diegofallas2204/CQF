```markdown
# Integración de IA en Courier Quest

Resumen:
- Se añaden agentes CPU con tres niveles de dificultad:
  - easy: RandomAI (elección/Movimiento aleatorio)
  - medium: HeuristicAI (horizonte limitado, evaluación heurística)
  - hard: GraphAI (A*, Dijkstra, planificación de rutas)

Integración:
- Se crea `Management/AIManager.py` que coordina la instancia de agente y la integra con Game.
- Game.py debe instanciar AIManager (ej.: `self.ai_manager = AIManager(difficulty="hard", planner=graph)`) y llamar `ai_manager.attach_game(self)` y `ai_manager.tick(delta_time)` durante el update loop.
- Para mover el agente CPU se propone exponer en Game un método `_attempt_move_cpu(ai_agent, dx, dy)` que reuse la lógica de física/resistencia/movimiento ya existente para el Player humano.

Recomendaciones:
- No duplicar lógica: reusar Player.move_to y City.is_walkable.
- Mantener la IA determinista en tests con seeds.
- Evitar cálculos pesados cada frame: construir el grafo (GraphBuilder) una vez y usar caches; replanificar sólo cuando cambie clima o cuando la ruta se vuelva inválida.
- Registrar decisiones en `enunciado_bitacora.md` (bitácora con prompts y decisiones de IA).
```