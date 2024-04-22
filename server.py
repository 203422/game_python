import asyncio
import json
import websockets
from random import randint

host = "0.0.0.0"
port = 5555

count_players = 0
clients = set()
state_movements = {}
lasers = []
lasers_hamsters = []
hamsters = []

players_ready = False
hamsters_removed = False
players_removed = False

def verify_players():
    global players_ready
    players_ready = all(player['ready'] for player in state_movements.values())

def setup_hamsters():
    x_distance = 48
    y_distance = 40
    x_offset = 70
    y_offset = 100

    for row_index in range(1, 5):
        for col_index in range(8):
            x = col_index * x_distance + x_offset
            y = row_index * y_distance + y_offset
            color = 'rojo' if row_index % 2 == 0 else 'verde'
            hamsters.append({'x': x, 'y': y, 'color': color, 'direction': 1})

async def update_state():
    global hamsters_removed, players_removed

    while True:  # Modificar el bucle para que siga ejecutándose incluso después de players_removed sea True
        if clients:  
            verify_players()
            if players_ready:
                
                handle_collisions()
                delete_hamster()

                if hamsters:  
                    move_hamsters() 

            for laser in lasers:
                laser['y'] -= laser['speed']
            for laser in lasers_hamsters:
                laser['y'] -= laser['speed']
            state = {
                'state_movements': state_movements,
                'lasers': lasers,
                'hamsters': hamsters,
                'lasers_hamsters': lasers_hamsters,
                'players_removed': players_removed
            }
            state_json = json.dumps(state)
            

            tasks = [asyncio.create_task(client.send(state_json)) for client in clients if client.open]
            if tasks:
                await asyncio.wait(tasks)

        await asyncio.sleep(0.05)



async def shoot_lasers_periodically():
    while not players_ready: 
        await asyncio.sleep(1)
    
    while True:
        await asyncio.sleep(1) 
        shoot_lasers_hamsters()

def shoot_lasers_hamsters():
    if hamsters:
        hamster_to_shoot = hamsters[randint(0, len(hamsters) - 1)]
        lasers_hamsters.append({'x': hamster_to_shoot['x'], 'y': hamster_to_shoot['y'], 'speed': -5})

def move_hamsters():
    global hamsters

    max_x = max(hamster['x'] for hamster in hamsters)
    min_x = min(hamster['x'] for hamster in hamsters)
    movement_speed = 5
    
    if max_x >= 600 - 48 or min_x <= 0:
        for hamster in hamsters:
            hamster['y'] += 5
            hamster['direction'] *= -1
            
    for hamster in hamsters:
        hamster['x'] += movement_speed * hamster['direction']

def handle_collisions():
    global players_removed, hamsters, lasers_hamsters, lasers
    for id_player, position in state_movements.items():
        for laser_hamster in lasers_hamsters:
            if position['x'] < laser_hamster['x'] < position['x'] + 45 and position['y'] < laser_hamster['y'] < position['y'] + 30:
                hamsters = []
                lasers_hamsters = []
                lasers = []
                players_removed = True
                
                   

def delete_player(player_id):
    if player_id in state_movements:
        del state_movements[player_id]
        print(f"Jugador {player_id} ha sido eliminado")
        if not state_movements:  #
            print("Todos los jugadores han sido eliminados. Deteniendo el juego.")
            loop.stop()

def delete_hamster():
    for laser in lasers:
        for hamster in hamsters:
            if hamster['x'] < laser['x'] < hamster['x'] + 48 and hamster['y'] < laser['y'] < hamster['y'] + 40:
                hamsters.remove(hamster)
                lasers.remove(laser)

async def manage_clients(socket):
    global count_players

    id_player = count_players
    count_players += 1
    state_movements[id_player] = {'x': 250, 'y': 570, 'ready': False, 'shoot': False}
    clients.add(socket)

    print(f"Player {id_player} se ha unido al servidor.")

    try:
        while True:
            data = await socket.recv()
            game_data = json.loads(data)
            if game_data.get('type') == 'shoot':
                lasers.append(game_data)
            else:
                state_movements[id_player].update(game_data)
            
            if not data:
                print(f'Conexión cerrada por el cliente: {id_player}')
                clients.remove(id_player)
                break
            
    except websockets.ConnectionClosed:
        print(f"Conexión del cliente {id_player} cerrada inesperadamente")
        clients.remove(socket)
        del state_movements[id_player] 
    finally:
        clients.remove(socket)
        if id_player in state_movements:
            del state_movements[id_player]
            print(f"Jugador {id_player} ha sido eliminado")


setup_hamsters()
server = websockets.serve(manage_clients, host, port)

loop = asyncio.get_event_loop()
loop.run_until_complete(server)
loop.create_task(update_state())
loop.create_task(shoot_lasers_periodically())  
loop.run_forever()
