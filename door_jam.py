#!/usr/bin/env python3
import math
import sys
import pygame
import threading
import time
from enum import Enum
import pytmx
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

def mul(a, b):
    x,y=a
    return (x*b, y*b)

def vmul(a, b):
    x1,y1=a
    x2,y2=b
    return (x1*x2, y1*y2)

NORTH = (0,-1)
EAST = (1,0)
SOUTH = (0,1)
WEST = (-1,0)

SCREEN_NORTH = (1,-1)
SCREEN_EAST = (1,1)
SCREEN_SOUTH = (-1,1)
SCREEN_WEST = (-1,-1)

def heading_to_screen(heading):
    return {
        NORTH:SCREEN_NORTH
        ,EAST:SCREEN_EAST
        ,SOUTH:SCREEN_SOUTH
        ,WEST:SCREEN_WEST
    }[heading]

def turn_left(h):
    return {
        NORTH:WEST
        ,EAST:NORTH
        ,SOUTH:EAST
        ,WEST:SOUTH
    }[h]

def turn_right(h):
    return {
        NORTH:EAST
        ,EAST:SOUTH
        ,SOUTH:WEST
        ,WEST:NORTH
    }[h]

def heading_name(h):
    return {
        NORTH:'north'
        ,EAST:'east'
        ,SOUTH:'south'
        ,WEST:'west'
    }[h]

class Animation:
    def __init__(self, filename, size, start_frame, end_frame):
        w,h = size
        self.img = pygame.image.load(filename)
        self.frame_width = w
        self.frame_height = h
        self.size = size
        self.n_frames = end_frame - start_frame + 1
        self.start_frame = start_frame
        (iw,ih) = self.img.get_size()
        frames_per_row = math.floor(iw/w)
        self.frames = [
            self.img.subsurface(pygame.Rect(
                (f%frames_per_row)*w, (f//frames_per_row)*h,
                self.frame_width, self.frame_height
            )) for f in range(start_frame, end_frame+1)
        ]

    def get_frame(self, n):
        i = (n % self.n_frames)
        return self.frames[i]

class Character:
    def __init__(self, marker, tile_unit):
        self.anims = {}
        self.tile_unit = tile_unit
        self.cur_anim = None
        self.cur_frame = 0
        self.size = None
        self.pos = (0,0)
        self.target = (0,0)
        self.destination = (0,0)
        self.selected = False
        self.marker = marker
        self.frames_per_tile = 20
        self.step_progress = 0
        self.path = None
        self.heading = EAST
        self.screen_heading = SCREEN_EAST
        self.selectable = True
        self.walking = False

    def is_selected(self):
        return self.selected

    def select(self):
        self.selected = True

    def clear_selection(self):
        self.selected = False

    def draw(self, surf, pos, scale):
        if self.cur_anim is None:
            return
        anim = self.anims[self.cur_anim]
        f = self.cur_frame
        img = anim.get_frame(f)
        lpos = add(pos, mul(vmul(self.screen_heading, mul(self.tile_unit, (self.step_progress/self.frames_per_tile)/2)), scale))

        newsize = mul(self.size, scale)
        scaled_char = pygame.transform.scale(img, newsize)

        surf.blit(scaled_char, lpos)
        if self.selected:
            newsize = mul(self.marker.size, scale)
            scaled_marker = pygame.transform.scale(self.marker.get_frame(f), newsize)
            surf.blit(scaled_marker, add(lpos, mul((16, -4), scale)))

    def next_frame(self):
        self.cur_frame += 1
        if self.pos != self.target or self.step_progress < 0:
            self.step_progress = self.step_progress + 1
            if self.step_progress >= self.frames_per_tile/2:
                self.pos = self.target
                self.step_progress = -(self.frames_per_tile/2)
            if self.step_progress == 0:
                self.walk_path(self.path)

    def add_anim(self, name, filename, size, start, end):
        a = Animation(filename, size, start, end)
        self.anims[name] = a
        if self.size is None:
            self.size = (a.frame_width, a.frame_height)

    def set_anim(self, name):
        self.cur_anim = name

    def warp_to(self, pos):
        self.pos = pos
        self.target = pos
        self.step_progress = 0

    def idle(self):
        self.target = self.pos
        self.destination = self.pos
        self.walking = False
        self.set_anim(
            {
                NORTH: 'idle_north'
                ,EAST: 'idle_east'
                ,SOUTH: 'idle_south'
                ,WEST: 'idle_west'
            }[self.heading]
        ) 

    def walk_path(self, path):
        self.step_progress = 0
        self.walking = True
        if path is not None:
            if len(path) > 0:
                self.destination = path[-1]
                [self.target, *self.path] = path
                if self.target == self.pos:
                    self.walk_path(self.path)
                else:
                    self.heading = sub(self.target, self.pos)
                    self.screen_heading = heading_to_screen(self.heading)
                    self.set_anim(
                        {
                            NORTH: 'walk_north'
                            ,EAST: 'walk_east'
                            ,SOUTH: 'walk_south'
                            ,WEST: 'walk_west'
                        }[self.heading]
                    )
            else:
                self.idle()
        else:
            self.idle()

class Game:
    def __init__(self):
        self.win = pygame.display.set_mode((1000,700), pygame.RESIZABLE)
        self.stop_event = threading.Event()
        self.can_render = threading.Event()
        self.can_render.set()
        self.last_time = time.time()
        self.font = pygame.font.SysFont("monospace", 18)
        self.big_font = pygame.font.SysFont("sans", 70)
        self.button_font = pygame.font.SysFont("sans", 40)
        self.tip_font = pygame.font.SysFont("sans", 18)
        self.guard_points = []
        self.levels = [
            'Tiled/Map1.tmx'
            ,'Tiled/Map2.tmx'
            ,'Tiled/Map3.tmx'
            ,'Tiled/Map4.tmx'
            ,'Tiled/Map5.tmx'
        ]
        self.cur_level = 0
        self.load_next_level()
        self.cursor = None
        self.selection = None
        self.path_plan = None

        self.retry_button = None
        self.game_is_over = False
        self.panning = False
        self.hover_occupied = None

        self.scale = 1
        self.scroll = 10

        self.three_frame = 0

        self.marker = Animation('Pointer.png', (16,16), 0, 15)

        self.restart_level()

    def load_next_level(self):
        self.load_map(self.levels[self.cur_level])
        self.cur_level += 1

    def restart_level(self):
        self.all_player_chars = []
        for c in self.char_points:
            player = self.load_character('Character1.png')
            player.warp_to(c)
            player.set_anim('idle_south')
            self.all_player_chars.append(player)

        self.guard = self.load_character('Guard.png')
        self.guard.selectable = False
        if self.guard_points:
            pos = self.guard_points[0]
            guard_path = [pos]
            for p in self.guard_points[1:]:
                guard_path.extend(nx.shortest_path(self.room, pos, p)[1:])
                pos = p
            new_paths = []

            if self.guard_start is not None:
                first_point = guard_path[0]
                line = self.line(self.guard_start, first_point)
                guard_path = [*line, *guard_path[1:]]
            self.guard.warp_to(guard_path[0])
            this_path = []
            for p in guard_path:
                door = self.door_from(p)
                if door is None:
                    this_path.append(p)
                else:
                    from_, to = door
                    this_path.append(p)
                    new_paths.append(this_path)
                    this_path = []

            if self.guard_end is not None:
                if len(this_path) >0:
                    last_point = this_path[-1]
                else:
                    last_point = new_paths[-1][-1]
                line = self.line(last_point, self.guard_end)
                this_path.extend(line)
            new_paths.append(this_path)
            next_path, *self.guard_paths = new_paths
            self.guard.walk_path(next_path)

        self.guard_state = 'walk'
        self.guard_done = False
        self.guard_passes = self.init_guard_passes

        self.all_guards = [self.guard]
        self.all_chars = self.all_guards + self.all_player_chars

        self.check_guard_vision()

        self.apply_scale()

    def door_from(self, pos):
        for (f,t) in self.doors:
            if f == pos:
                return (f,t)
        return None

    def load_character(self, sprite_sheet, size=(48,48)):
        new_char = Character(self.marker, (self.tw, self.th))
        for i, heading in enumerate(['east', 'south', 'west', 'north']):
            new_char.add_anim(f'idle_{heading}', sprite_sheet, size, i*9, i*9)
            new_char.add_anim(f'walk_{heading}', sprite_sheet, size, (i*9)+1, (i*9)+8)
        new_char.set_anim('idle_east')
        new_char.warp_to((0,0))
        return new_char

    def grid_to_surface(self, x, y):
        return grid_to_surface(x,y,self.w,self.h,self.tw,self.th)

    def surface_to_grid(self, x, y):
        return surface_to_grid(x,y,self.w,self.h,self.tw,self.th)

    def coords(self, pos, size=None):
        if size is None:
            size = (self.tw/2, self.th)
        delta = sub((self.tw/2, self.th), size)
        return add(self.offset, mul(add(delta, self.grid_to_surface(*pos)),self.scale))

    def load_map(self, name):
        self.map = load_tmx(name)
        self.w = self.map.width
        self.h = self.map.height
        self.tw = self.map.tilewidth
        self.th = self.map.tileheight
        self.sw, self.sh = surface_geom(self.w, self.h, self.tw, self.th)
        self.map_surface = pygame.Surface((self.sw,self.sh))
        self.overlay_surface = pygame.Surface((self.sw,self.sh))
        self.overlay_surface.convert_alpha()
        self.overlay_surface.set_alpha(255)
        self.map_parts = {}
        self.doors = []
        g = nx.Graph()
        layer_id = lambda layer: next(i for i, l in enumerate(self.map.layers) if l==layer)
        def layer_by_name(name):
            try:
                return self.map.get_layer_by_name(name)
            except ValueError:
                return None
        for layer,name in [(layer_by_name(name),name) for name in ['Floor', 'Walls', 'Doors', 'GuardEntrance', 'GuardExit']]:
            if not isinstance(layer, pytmx.pytmx.TiledTileLayer):
                continue
            for x, y, img_gid in layer.iter_data():
                img = self.map.get_tile_image_by_gid(img_gid)
                if img is None:
                    continue
                delta = sub((self.tw/2, self.th), img.get_size())
                pos = add(self.grid_to_surface(x,y), delta)
                if name == 'Floor':
                    self.map_surface.blit(img, pos)
                elif name.startswith('Guard'):
                    self.overlay_surface.blit(img, pos)
                else:
                    depth = x+y+1
                    part = self.map_parts.get(depth)
                    if part is None:
                        part = pygame.Surface((self.sw, self.th*2))
                        self.map_parts[depth]=part
                    part.blit(img, sub(pos, (0,-self.th+((depth-1)*(self.th/2)))))
                props = self.map.get_tile_properties_by_gid(img_gid)
                if props and props.get('floor', False):
                    g.add_node((x,y))
                    for ox, oy in [(x-1,y),(x,y-1)]:
                        other = self.map.get_tile_properties(ox, oy, layer_id(layer))
                        if other and other.get('floor',False):
                            g.add_edge((x,y), (ox,oy))
                east_wall = props is not None and props.get('wall_east', False)
                south_wall = props is not None and props.get('wall_south', False)
                east_door = props is not None and props.get('door_east', False)
                south_door = props is not None and props.get('door_south', False)
                to_remove = []
                if east_wall:
                    other = add(EAST, (x,y))
                    to_remove.append(((x,y), other))
                if south_wall:
                    other = add(SOUTH, (x,y))
                    to_remove.append(((x,y), other))
                if east_door:
                    other = add(EAST, (x,y))
                    self.doors.append(((x,y), other))
                    self.doors.append((other, (x,y)))
                if south_door:
                    other = add(SOUTH, (x,y))
                    self.doors.append(((x,y), other))
                    self.doors.append((other, (x,y)))
                for from_, to in to_remove:
                    try:
                        g.remove_edge(from_, to)
                    except nx.NetworkXError:
                        pass
        self.offset = (100,100)
        self.room = g
        points = layer_by_name('Points')
        self.rooms = []

        self.guard_start = None
        self.guard_end = None
        self.guard_on_point = False
        self.char_points = []
        if points:
            guard_points = {}
            for p in points:
                props = p.properties
                if props.get('guard_start', False):
                    self.guard_start = (math.floor(p.x/self.th),math.floor(p.y/self.th))
                if props.get('guard_end', False):
                    self.guard_end = (math.floor(p.x/self.th),math.floor(p.y/self.th))
                passes = props.get('guard_passes')
                if passes is not None:
                    self.init_guard_passes = passes
                    self.guard_passes = passes
                    self.guard_pass_point = (math.floor(p.x/self.th),math.floor(p.y/self.th))
                if 'index' in props:
                    i = props['index']
                    guard_points[i] = (math.floor(p.x/self.th),math.floor(p.y/self.th))
                else:
                    x,y,w,h = [math.floor(a/self.th) for a in [p.x, p.y, p.width, p.height]]
                    is_goal = props.get('goal', False)
                    start, end = ((x,y),(x+w,y+h))
                    self.rooms.append((start, end))
                    if is_goal:
                        self.goal_room = (start, end)
                if props.get('character', False):
                    self.char_points.append((math.floor(p.x/self.th),math.floor(p.y/self.th)))
                    
            self.guard_points = [guard_points [k] for k in sorted(guard_points.keys())]


    def line(self, from_, to):
        fx, fy = from_
        tx, ty = to
        line = [from_]
        x, y = from_
        if fx==tx:
            dir_ = 1 if ty>fy else -1
            while (x,y) != to:
                y += dir_
                line.append((x,y))
        if fy==ty:
            dir_ = 1 if tx>fx else -1
            while (x,y) != to:
                x += dir_
                line.append((x,y))
        return line


    def squares_in_room(self, start, end):
        room_squares = []
        sx,sy=start
        ex,ey=end
        for x in range(sx,ex):
            for y in range(sy,ey):
                room_squares.append((x,y))
        return room_squares

    def is_in_room(self, pos, start, end):
        sx,sy=start
        ex,ey=end
        x,y=pos
        return all([
            x>=sx
            ,x<ex
            ,y>=sy
            ,y<ey
        ])

    def game_over(self):
        self.game_is_over = True

    def check_guard_vision(self):
        p = self.guard.pos
        seen_points = [p]
        for room in self.rooms:
            if self.is_in_room(p, *room):
                seen_points.extend(self.squares_in_room(*room))
        h = self.guard.heading
        next_tile = add(p, h)
        while self.room.has_edge(p, next_tile):
            seen_points.append(next_tile)
            p = next_tile
            next_tile = add(next_tile, h)
        self.guard_vision = seen_points
        for tile in seen_points:
            for c in self.all_player_chars:
                if tile == c.pos:
                    self.game_over()

    def winning_condition(self):
        return self.guard_done and all(self.is_in_room(c.pos, *self.goal_room) for c in self.all_player_chars)
        
    def update(self, timediff):
        if not self.game_is_over:
            # Characters move one animation frame every 3 game frames
            self.three_frame = (self.three_frame + 1) % 2
            if self.three_frame == 0:
                for c in self.all_chars:
                    c.next_frame()
                match self.guard_state:
                    case 'walk':
                        if self.guard.pos == self.guard_pass_point and not self.guard_on_point:
                            self.guard_on_point = True
                            self.guard_passes -= 1
                            if self.guard_passes == 0:
                                self.guard_done = True
                        if self.guard.pos != self.guard_pass_point and self.guard_on_point:
                            self.guard_on_point = False
                        if not self.guard.walking:
                            door = self.door_from(self.guard.pos)
                            if door is not None:
                                from_, to = door
                                self.guard.walk_path([to])
                                self.guard_exit = from_
                                self.guard_counter = 0
                                self.guard_state = 'enter_room'
                            else:
                                self.guard_done = True
                    case 'enter_room':
                        if not self.guard.walking:
                            if self.guard_counter == 0:
                                new_heading = turn_left(self.guard.heading)
                                self.guard.heading = new_heading
                                self.guard.idle()
                            if self.guard_counter == 10:
                                new_heading = turn_right(self.guard.heading)
                                self.guard.heading = new_heading
                                self.guard.idle()
                            if self.guard_counter == 20:
                                new_heading = turn_right(self.guard.heading)
                                self.guard.heading = new_heading
                                self.guard.idle()
                            if self.guard_counter > 30:
                                next_path, *self.guard_paths = self.guard_paths
                                self.guard.walk_path([self.guard_exit, *next_path])
                                self.guard_state = 'walk'
                            self.guard_counter += 1
                self.check_guard_vision()

    def draw_cursor(self, pos, color):
        cx,cy = pos
        gx,gy = add(self.offset, self.grid_to_surface(cx,cy))
        gx,gy = self.coords((cx,cy))
        s = self.scale
        pygame.draw.aalines(self.win, color, True, [
            (gx,gy)
            ,(gx+(self.tw/2*s), gy+(self.th/2*s))
            ,(gx,gy+self.th*s)
            ,(gx-(self.tw/2*s), gy+(self.th/2*s))
        ])

    def draw_box(self, pos, color):
        cx,cy = pos
        gx,gy = add(self.offset, self.grid_to_surface(cx,cy))
        gx,gy = self.coords((cx,cy))
        s = self.scale
        pygame.draw.polygon(self.win, color, [
            (gx,gy)
            ,(gx+(self.tw/2*s), gy+(self.th/2*s))
            ,(gx,gy+self.th*s)
            ,(gx-(self.tw/2*s), gy+(self.th/2*s))
        ])

    def draw_path(self, path, color):
        if len(path) < 2:
            return
        pygame.draw.aalines(self.win, color, False, [
            add(self.offset, mul(add(self.grid_to_surface(*p), (0, self.th/2)), self.scale)) for p in path
        ])

    def render(self):
        self.win.fill((0,0,0))
        self.win.blit(self.scaled_map, self.offset)
        self.win.convert_alpha()
        self.win.set_alpha(255)
        if self.cursor is not None:
            self.draw_cursor(self.cursor, (0,255,0))
        if self.selection is not None:
            self.draw_cursor(self.selection, (0,255,0))
        if self.hover_occupied is not None:
            self.draw_cursor(self.hover_occupied, (255,0,0))
        if self.path_plan is not None:
            self.draw_path(self.path_plan, (0,0,255))
        for p in self.guard_vision:
            self.draw_cursor(p, (255,238,77))
        chars_for_depth = {}
        for c in self.all_chars:
            pos = self.coords(c.pos, c.size)
            cx,cy=c.pos
            depth = cx+cy
            chars = chars_for_depth.get(depth, None)
            if chars is None:
                chars = list()
                chars_for_depth[depth] = chars
            chars.append(c)
        for depth in range(0, self.w+self.h):
            part = self.scaled_map_parts.get(depth)
            if part is not None:
                self.win.blit(part, add(self.offset, (0,math.ceil(self.scale * (-self.th+(depth-1) * (self.th/2))))))
            chars = chars_for_depth.get(depth, [])
            for char in chars:
                pos = self.coords(char.pos, char.size)
                char.draw(self.win, pos, self.scale)
        self.win.blit(self.scaled_overlay, self.offset)
        if self.game_is_over:
            msg = self.big_font.render(f"You got caught! Game Over!", 1, (255,0,0))
            msg_pos = sub(mul(self.win.get_size(), 1/2), mul(msg.get_size(), 1/2))
            self.win.blit(msg, msg_pos)
            msg = self.button_font.render(f"retry", 1, (0,0,255))
            msg_pos = add(sub(mul(self.win.get_size(), 1/2), mul(msg.get_size(), 1/2)), (0,70))
            (x,y) = sub(msg_pos, (5,5))
            (w,h) = sub(add(msg_pos, add((5,5), msg.get_size())), (x,y))
            self.retry_button = pygame.Rect(x, y, w, h)
            color = (155,155,155)
            if self.retry_button.collidepoint(self.last_mouse_pos):
                color = (255,255,255)
            pygame.draw.rect(self.win, color, self.retry_button)
            self.win.blit(msg, msg_pos)
        else:
            self.retry_button = None

        if self.winning_condition():
            msg = self.big_font.render(f"You made it!", 1, (0,255,0))
            msg_pos = sub(mul(self.win.get_size(), 1/2), mul(msg.get_size(), 1/2))
            self.win.blit(msg, msg_pos)
            msg = self.button_font.render(f"next level", 1, (0,0,255))
            msg_pos = add(sub(mul(self.win.get_size(), 1/2), mul(msg.get_size(), 1/2)), (0,70))
            (x,y) = sub(msg_pos, (5,5))
            (w,h) = sub(add(msg_pos, add((5,5), msg.get_size())), (x,y))
            self.next_button = pygame.Rect(x, y, w, h)
            color = (155,155,155)
            if self.next_button.collidepoint(self.last_mouse_pos):
                color = (255,255,255)
            pygame.draw.rect(self.win, color, self.next_button)
            self.win.blit(msg, msg_pos)           
        else:
            self.next_button = None

    def apply_scale(self):
        ssize = mul(self.map_surface.get_size(), self.scale)
        self.scaled_map = pygame.transform.scale(self.map_surface, ssize)
        self.scaled_overlay = pygame.transform.scale(self.overlay_surface, ssize)
        self.scaled_map.convert_alpha()
        self.scaled_overlay.convert_alpha()
        self.scaled_map.set_alpha(255)
        self.scaled_overlay.set_alpha(255)
        self.scaled_map_parts = {}
        for depth in self.map_parts:
            part = self.map_parts[depth]
            ssize = mul(part.get_size(), self.scale)
            self.scaled_map_parts[depth] = pygame.transform.scale(part, ssize)
            self.scaled_map_parts[depth].convert_alpha()
            self.scaled_map_parts[depth].set_colorkey((0, 0, 0))

    def to_cursor_pos(self, pos):
        mouse_pos = mul(sub(pos, self.offset), 1/self.scale)
        return self.surface_to_grid(*mouse_pos)

    def select_character(self, pos):
        selected = None
        for c in self.all_chars:
            if selected is None and c.pos == pos and c.selectable and not c.walking:
                c.select()
                selected = c
            else:
                c.clear_selection()
        return selected

    def space_is_free(self, pos):
        return not any(c.destination== pos for c in self.all_player_chars)
            
    def event(self, ev):
        match ev.type:
            case pygame.MOUSEMOTION:
                self.last_mouse_pos = ev.pos
                mouse_pos = self.to_cursor_pos(ev.pos)
                props = None
                try:
                    props = self.map.get_tile_properties(*mouse_pos,0)
                except Exception:
                    pass
                if props and props.get('floor',False):
                    if not self.selection or self.space_is_free(mouse_pos):
                        self.cursor = mouse_pos
                        self.hover_occupied = None
                        if self.selection:
                            self.path_plan = nx.shortest_path(self.room, self.selection, self.cursor)
                        else:
                            self.path_plan = None
                    else:
                        self.hover_occupied = mouse_pos
                        self.path_plan = None
                        self.cursor = None
                else:
                    self.cursor = None
                    self.path_plan = None
                    self.hover_occupied = None
                if self.panning:
                    self.offset = add(self.pan_start_offset, sub(ev.pos, self.pan_start_mouse))
            case pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    if self.winning_condition() and self.next_button is not None:
                        if self.next_button.collidepoint(self.last_mouse_pos):
                            self.load_next_level()
                            self.restart_level()
                    if self.game_is_over and self.retry_button is not None:
                        if self.retry_button.collidepoint(self.last_mouse_pos):
                            self.game_is_over = False
                            self.restart_level()
                    if self.selection:
                        if self.cursor:
                            self.selected_char.walk_path(self.path_plan)
                        self.selected_char.clear_selection()
                        self.path_plan = None
                        self.selection = None
                        self.selected_char = None
                    else:
                        char = self.select_character(self.cursor)
                        if char is not None:
                            self.selection = self.cursor
                            self.path_plan = None
                            self.selected_char = char
                if ev.button == 2:
                    self.panning = True
                    self.pan_start_offset = self.offset
                    self.pan_start_mouse = ev.pos
            case pygame.MOUSEBUTTONUP:
                if ev.button == 2:
                    self.panning = False
            case pygame.MOUSEWHEEL:
                self.scroll = max(5, min(100, self.scroll + ev.y))
                old_scale = self.scale
                self.scale = self.scroll/10
                self.offset = sub(self.last_mouse_pos, mul(mul(sub(self.last_mouse_pos, self.offset), 1/old_scale), self.scale))
                self.apply_scale()
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
