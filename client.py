import pygame
import sys
from random import randint
import asyncio
from pygame.locals import *
import json
import websockets

host = "0.0.0.0"
port = 5555

player_state = {'x': 250, 'y': 570, 'ready': False, 'shoot': False}
state_movements = {}
lasers = []
hamsters = []
lasers_hamsters = []
players_ready = False
player_ready = False
players_removed = False

def load_fill(screen):
    screen.fill((30,30,30))

def create_lines(screen, width, height):
    line_height = 3
    line_amount = int(height / line_height)
    for line in range(line_amount):
        y_pos = line * line_height
        pygame.draw.line(screen, 'black', (0, y_pos), (width, y_pos), 1)

def drawTv(screen, tv_image, width, height):
    tv_image.set_alpha(randint(75, 90))
    create_lines(screen, width, height)
    screen.blit(tv_image, (0, 0))

async def update_state(socket):
    global state_movements, lasers, hamsters, lasers_hamsters, players_ready, player_count, players_removed
    data = await socket.recv()
    if data:
        state = json.loads(data)
        state_movements = state['state_movements']
        lasers = state['lasers']
        hamsters = state['hamsters']
        lasers_hamsters = state.get('lasers_hamsters', [])
        players_removed = state['players_removed']    
        players_ready = all(player['ready'] for player in state_movements.values())
        player_count = len(state_movements)

def display_init(screen):
    if not player_ready:
        font = pygame.font.Font('assets/fuentes/Pixeled.ttf', 10)
        text_surface = font.render('Presiona espacio si estas listo!', True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        text_rect.y += 20
        screen.blit(text_surface, text_rect)

        
def display_victory(screen):
    font = pygame.font.Font('assets/fuentes/Pixeled.ttf', 20)
    text_surface = font.render('Consiguieron el burrito!', True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(text_surface, text_rect)

def load_music():
    music = pygame.mixer.Sound('assets/audio/intro.wav')
    music.set_volume(0.1)
    music.play(loops = -1)


def display_player_count(screen, player_count):
    font = pygame.font.Font('assets/fuentes/Pixeled.ttf', 10)
    text_surface = font.render(f'Jugadores listos: {player_count} / 2', True, (255, 255, 255))
    screen.blit(text_surface, (10, 10))

def loss_screen(screen):
    font = pygame.font.Font('assets/fuentes/Pixeled.ttf', 10)
    text_surface = font.render('Han perdido!', True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(text_surface, text_rect)
    

async def send_movements(socket):
    await socket.send(json.dumps(player_state))
    await update_state(socket)

async def send_lasers(socket, laser_position):
    await socket.send(json.dumps(laser_position))


async def main():
    player_count = 0
    pygame.init()
    width, height = 600, 600
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Hamsters vs Esqueleto")
    font = pygame.font.Font('assets/fuentes/Pixeled.ttf', 5)
    tv = pygame.image.load('assets/graficos/tv.png').convert_alpha()
    tv = pygame.transform.scale(tv, (width, height))
    hamster_red_img = pygame.image.load('assets/graficos/rojo.png').convert_alpha()
    hamster_green_img = pygame.image.load('assets/graficos/verde.png').convert_alpha()
    player_img = pygame.image.load('assets/graficos/jugador.png')
    laser_sound = pygame.mixer.Sound('assets/audio/laser.wav')
    laser_sound.set_volume(0.1)

    laser_shot = False
    last_shot_time = 0
    shoot_cooldown = 600

    async with websockets.connect(f"ws://{host}:{port}") as socket:

        clock = pygame.time.Clock()
        
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == KEYDOWN and event.key == K_SPACE:
                    player_state['ready'] = True
                    player_ready = True
                    await send_movements(socket)               
                
            
            keys = pygame.key.get_pressed()

            if keys[K_a] and player_state['x'] > 0:
                player_state['x'] -= 5
            if keys[K_d] and player_state['x'] < 600:
                player_state['x'] += 5
            current_time = pygame.time.get_ticks()
            if keys[K_w] and not laser_shot and current_time - last_shot_time > shoot_cooldown:
                laser_sound.play()
                player_state['shoot'] = True
                laser = {'type': 'shoot', 'x': player_state['x'], 'y': player_state['y'], 'speed': 5}
                await send_lasers(socket, laser)
                laser_shot = True
                last_shot_time = current_time
            elif not keys[K_w]:
                laser_shot = False

            await send_movements(socket)
            player_state['shoot'] = False

            load_fill(screen)
            drawTv(screen, tv, width, height)

            if players_ready == False:
                display_init(screen)        

            if players_ready:
                load_music()
                      
            players_re = sum(1 for player in state_movements.values() if 'ready' in player and player['ready'])
            total_players = len(state_movements)
            if players_ready < total_players:
                message = f'Jugadores listos: ({players_re}/{total_players})'


            font = pygame.font.Font('assets/fuentes/Pixeled.ttf', 10)
            message_text = font.render(message,  True, (255, 255, 255))
            screen.blit(message_text, (10, 10))


            for hamster in hamsters:  
                hamster_img = hamster_red_img if hamster['color'] == 'rojo' else hamster_green_img
                hamster_img = pygame.transform.scale(hamster_img, (48, 40))
                screen.blit(hamster_img, (hamster['x'], hamster['y']))

            for id_player, position in state_movements.items():
                player = pygame.transform.scale(player_img, (45, 30))
                screen.blit(player, (position['x'], position['y']))

                tag_name = font.render(f'Jugador {id_player}', True, (255, 255, 255))
                screen.blit(tag_name, (position['x'], position['y'] - 10))

            for laser in lasers:
                pygame.draw.rect(screen, (255, 255, 255), (laser['x'] + 15, laser['y'], 5, 20))

            for laser in lasers_hamsters:  
                pygame.draw.rect(screen, (255, 0, 0), (laser['x'] + 15, laser['y'], 5, 20)) 
            
            if not hamsters and players_ready and players_removed == False:
                display_victory(screen)

            if players_removed:
                loss_screen(screen)


            pygame.display.update()


            clock.tick(60)


asyncio.run(main())
