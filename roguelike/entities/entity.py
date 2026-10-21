from __future__ import annotations


class Entity:
    def __init__(
        self,
        x: int,
        y: int,
        tile: str,
        name: str,
        blocks_movement: bool = False,
    ) -> None:
        self.x = x
        self.y = y
        self.tile = tile
        self.name = name
        self.blocks_movement = blocks_movement
        self.flash_timer: int = 0
        self.last_known_x: int | None = None
        self.last_known_y: int | None = None

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy