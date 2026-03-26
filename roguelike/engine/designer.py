import pygame
import random
from pathlib import Path
from engine.palette import *

class DrawingStep:
    def __init__(self, shape: str, color: tuple, points: list):
        self.shape = shape
        self.color = color
        self.points = points

class ProceduralDesigner:
    def __init__(self):
        self.active = False
        self.steps: list[DrawingStep] = []
        self.mirror_mode = True
        self.current_color = OLD_GOLD # Default Gold
        self.tool = "polygon" # "rect", "circle", "line", "polygon"
        self.working_points = []

    def add_point(self, x: int, y: int):
        self.working_points.append((x, y))
        # Polygons are finished manually; others finish based on point count
        if self.tool == "rect" and len(self.working_points) == 2:
            self.commit_shape()
        elif self.tool == "circle" and len(self.working_points) == 2:
            self.commit_shape()
        elif self.tool == "line" and len(self.working_points) == 2:
            self.commit_shape()

    def commit_shape(self):
        if not self.working_points: return
        self.steps.append(DrawingStep(self.tool, self.current_color, list(self.working_points)))
        
        if self.mirror_mode:
            mirrored = [(64 - px, py) for px, py in self.working_points]
            self.steps.append(DrawingStep(self.tool, self.current_color, mirrored))
            
        self.working_points = []

    def export_code(self, name: str):
        func_name = f"_draw_{name.lower().replace(' ', '_')}"
        lines = [
            f"def {func_name}(surf: pygame.Surface, rng: random.Random) -> None:",
            "    surf.fill(VOID_BLACK)"
        ]
        for s in self.steps:
            if s.shape == "polygon":
                lines.append(f"    pygame.draw.polygon(surf, {s.color}, {s.points})")
            elif s.shape == "rect":
                x, y = s.points[0]
                w, h = s.points[1][0] - x, s.points[1][1] - y
                lines.append(f"    pygame.draw.rect(surf, {s.color}, ({x}, {y}, {w}, {h}))")
            elif s.shape == "circle":
                center = s.points[0]
                radius = int(((s.points[1][0]-center[0])**2 + (s.points[1][1]-center[1])**2)**0.5)
                lines.append(f"    pygame.draw.circle(surf, {s.color}, {center}, {radius})")
        
        path = Path(f"generated_{name}.py")
        path.write_text("\n".join(lines))
        return str(path.absolute())