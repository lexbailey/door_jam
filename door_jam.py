#!/usr/bin/env python3
import math
import sys
import pygame
import threading
import time
from enum import Enum
from pytmx.util_pygame import load_pygame as load_tmx
import traceback
import networkx as nx

target_fps = 30

RENDER = pygame.event.custom_type()

def surface_geom(w, h, tw, th):
    return (
        ((w*tw) + (h*tw)) /2
        ,((h*th) + (w*th)) /2
    )

def grid_to_surface(x, y, w, h, tw, th):
    """ Converts grid coordinates to screen coordinates
    with 0,0 on the top corner of the topmost tile in the map """
    return (
        ((tw * (h-1)) + ((x-y)*tw)) / 2
        ,((x+y)*th) / 2
    )

def surface_to_grid(x, y, w, h, tw, th):
    x_plus_y = (y*2)/th
    x_minus_y = ((x*2) - (tw * (h-1)))/tw
    sx = (x_plus_y + x_minus_y) / 2
    sy = x_plus_y - sx
    return (
        math.floor(sx)
        ,math.floor(sy)
    )

def add(c1,c2):
    ((x1,y1),(x2,y2)) = (c1,c2)
    return (
        x1+x2
        ,y1+y2
    )

def neg(c1):
    (x,y) = c1
    return (-x,-y)

def sub(c1,c2):
    return add(c1, neg(c2))

class Game:
    def __init__(self):
        self.win = pygame.display.set_mode((1000,700))
        self.stop_event = threading.Event()
        self.can_render = threading.Event()
        self.can_render.set()
        self.image = pygame.image.load("image.png")
        self.last_time = time.time()
        self.font = pygame.font.SysFont("monospace", 18)
        self.load_map('Tiled/Map1.tmx')
        self.cursor = None
        self.selection = None
        self.path_plan = None

    def grid_to_surface(self, x, y):
        return grid_to_surface(x,y,self.w,self.h,self.tw,self.th)

    def surface_to_grid(self, x, y):
        return surface_to_grid(x,y,self.w,self.h,self.tw,self.th)

    def load_map(self, name):
        self.map = load_tmx(name)
        self.w = self.map.width
        self.h = self.map.height
        self.tw = self.map.tilewidth
        self.th = self.map.tileheight
        self.sh, self.sw = surface_geom(self.w, self.h, self.tw, self.th)
        self.map_surface = pygame.Surface((self.sh,self.sw))
        g = nx.Graph()
        for i, layer in enumerate(self.map.visible_layers):
            for x, y, img in layer.tiles():
                delta = sub((self.tw/2, self.th), img.get_size())
                pos = add(self.grid_to_surface(x,y), delta)
                self.map_surface.blit(img, pos)
                props = self.map.get_tile_properties(x, y, i)
                if props and props['floor']:
                    g.add_node((x,y))
                    for ox, oy in [(x-1,y),(x,y-1)]:
                        other = self.map.get_tile_properties(ox, oy, i)
                        if other and other['floor']:
                            g.add_edge((x,y), (ox,oy))
        x,y=self.grid_to_surface(45,45)
        self.offset = (-x+300,-y+100)
        self.room = g

    def update(self, timediff):
        pass

    def draw_cursor(self, pos, color):
        cx,cy = pos
        gx,gy = add(self.offset, self.grid_to_surface(cx,cy))
        pygame.draw.aalines(self.win, color, True, [
            (gx,gy)
            ,(gx+(self.tw/2), gy+(self.th/2))
            ,(gx,gy+self.th)
            ,(gx-(self.tw/2), gy+(self.th/2))
        ])

    def draw_path(self, path, color):
        if len(path) < 2:
            return
        pygame.draw.aalines(self.win, color, False, [
            add(add(self.offset, self.grid_to_surface(*p)), (0, self.th/2)) for p in path
        ])

    def render(self):
        self.win.fill((0,0,0))
        self.win.blit(self.map_surface, self.offset)
        if self.cursor is not None:
            self.draw_cursor(self.cursor, (255,0,0))
        if self.selection is not None:
            self.draw_cursor(self.selection, (0,255,0))
        if self.path_plan is not None:
            self.draw_path(self.path_plan, (255,255,0))

    def to_cursor_pos(self, pos):
        mouse_pos = sub(pos, self.offset)
        return self.surface_to_grid(*mouse_pos)
            
    def event(self, ev):
        match ev.type:
            case pygame.MOUSEMOTION:
                mouse_pos = self.to_cursor_pos(ev.pos)
                props = self.map.get_tile_properties(*mouse_pos,0)
                if props and props['floor']:
                    self.cursor = mouse_pos
                    if self.selection:
                        self.path_plan = nx.shortest_path(self.room, self.selection, self.cursor)
                    else:
                        self.path_plan = None
                else:
                    self.cursor = None
                    self.path_plan = None
            case pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    self.selection = self.cursor
                    self.path_plan = None
            case _:
                print(f"Unknown event: {ev}")

    def fps_counter(self, diff):
        fps = 1/diff
        count = self.font.render(f"FPS: {int(fps)}/30", 1, (255,255,255))
        self.win.blit(count, (1, 1))

    def quit(self):
        self.stop_event.set()

    def render_poll(self):
        while not self.stop_event.is_set():
            self.can_render.wait()
            self.can_render.clear()
            pygame.fastevent.post(pygame.event.Event(RENDER, {}))
            time.sleep(1/target_fps)

    def run(self):
        threading.Thread(target=self.render_poll).start()
        try:
            while ev := pygame.fastevent.wait():
                match ev.type:
                    case pygame.QUIT:
                        break
                    case _RENDER if _RENDER == RENDER:
                        now = time.time()
                        diff = now - self.last_time
                        self.last_time = now
                        try:
                            self.update(diff)
                            self.render()
                        except Exception as e:
                            traceback.print_exception(e, file=sys.stderr)
                        self.fps_counter(diff)
                        pygame.display.flip()
                        self.can_render.set()
                    case _:
                        try:
                            self.event(ev)
                        except Exception as e:
                            traceback.print_exception(e, file=sys.stderr)
        except KeyboardInterrupt:
            pass
        self.quit()

def main():
    pygame.init()
    pygame.fastevent.init()
    game = Game()
    game.run()

if __name__=="__main__":
    main()
