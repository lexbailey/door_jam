#!/usr/bin/env python3
import pygame
import threading
import time
from enum import Enum

target_fps = 30

RENDER = pygame.event.custom_type()

class Game:
    def __init__(self):
        self.win = pygame.display.set_mode((1000,700))
        self.stop_event = threading.Event()
        self.image = pygame.image.load("image.png")
        self.last_time = time.time()
        self.font = pygame.font.SysFont("monospace", 18)
        self.sprite_x = 10.0
        self.start_speed = 200.0 # pixels per second
        self.cur_speed = self.start_speed

    def update(self, timediff):
        self.sprite_x += timediff*self.cur_speed
        if self.sprite_x > 600.0:
            self.cur_speed = -self.start_speed
        if self.sprite_x < 10.0:
            self.cur_speed = self.start_speed

    def render(self):
        self.win.fill((0,0,0))
        self.win.blit(self.image, (50,self.sprite_x))

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
        self.quit()

def main():
    pygame.init()
    pygame.fastevent.init()
    game = Game()
    game.run()

if __name__=="__main__":
    main()
