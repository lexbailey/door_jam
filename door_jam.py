#!/usr/bin/env python3
import sys
import pygame
import threading
import time
from enum import Enum
from pytmx.util_pygame import load_pygame as load_tmx

target_fps = 30

RENDER = pygame.event.custom_type()

def surface_geom(w, h, tw, th):
    return (
        ((w*tw) + (h*tw)) /2
        ,((h*th) + (w*th)) /2
    )

def grid_to_surface(x, y, w, h, tw, th):
    return (
        ((tw * (h-1))/2) + (((x-y)*tw)/2)
        ,((x+y)*th)/2
    )

def surface_to_grid(x, y):
    pass

class Game:
    def __init__(self):
        self.win = pygame.display.set_mode((1000,700))
        self.stop_event = threading.Event()
        self.image = pygame.image.load("image.png")
        self.last_time = time.time()
        self.font = pygame.font.SysFont("monospace", 18)
        self.load_map('Tiled/Map1.tmx')

    def grid_to_surface(self, x, y):
        return grid_to_surface(x,y,self.w,self.h,self.tw,self.th)

    def load_map(self, name):
        self.map = load_tmx(name)
        self.w = self.map.width
        self.h = self.map.height
        self.tw = self.map.tilewidth
        self.th = self.map.tileheight
        self.sh, self.sw = surface_geom(self.w, self.h, self.tw, self.th)
        self.map_surface = pygame.Surface((self.sh,self.sw))
        for layer in self.map.visible_layers:
            for x, y, img in layer.tiles():
                self.map_surface.blit(img, self.grid_to_surface(x,y))

    def update(self, timediff):
        pass

    def render(self):
        self.win.fill((0,0,0))
        x,y=self.grid_to_surface(45,45)
        self.win.blit(self.map_surface, (-x+300,-y+100))

    def event(self, ev):
        print(f"Unknown event: {ev}")

    def fps_counter(self, diff):
        fps = 1/diff
        count = self.font.render(f"FPS: {int(fps)}/30", 1, (255,255,255))
        self.win.blit(count, (1, 1))

    def quit(self):
        self.stop_event.set()

    def render_poll(self):
        while not self.stop_event.is_set():
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
                        self.update(diff)
                        self.render()
                        self.fps_counter(diff)
                        pygame.display.flip()
                    case _:
                        self.event(ev)
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
