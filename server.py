import socket
import asyncio
import json
import aiosqlite
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from constants import *

ph = PasswordHasher()

async def broadcast_message(message):
    print(f'Broadcast: {message.strip()}')
    msg_bytes = message.encode()
    global ALL_USERS
    for _, (_, writer) in ALL_USERS.items():
        writer.write(msg_bytes)
        await writer.drain()

async def send_message(reader, writer, message):
    writer.write(message.encode())
    await writer.drain()


async def login(uname, password):
    try:
        async with aiosqlite.connect('user.db') as db:
            async with db.execute('SELECT password FROM user WHERE username = ?', (uname,)) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return uname, ERR, "User not found"
                stored_password = row[0]
                try:
                    ph.verify(stored_password, password)
                    return uname, OK, "Login successful"
                except VerifyMismatchError:
                    return uname, ERR, "Incorrect password"
    except Exception as e:
        return uname, ERR, str(e)

async def signup(uname, password):
    print("Inside signup")
    try:
        hashed_password = ph.hash(password)
        async with aiosqlite.connect('user.db') as db:
            await db.execute('INSERT INTO user (username, password) VALUES (?, ?)', (uname, hashed_password))
            await db.commit()
        return uname, OK, "Signup successful"
    except aiosqlite.IntegrityError:
        return uname, ERR, "Username already exists"
    except Exception as e:
        return uname, ERR, str(e)
    
async def authenticate_user(reader, writer):
    data = {}

    query = await reader.readline()
    data = json.loads(query.decode())
    print(data)
    name, status, message = None, False, "Invalid request"
    if data['type'] == LOGIN:
        result = await login(data['username'], data['password'])
        name, status, message = result  
    elif data['type'] == SIGNUP:
        result = await signup(data['username'], data['password'])
        name, status, message = result

    
    response = {}
    response['status'] = status
    response['message'] = message
    response['recipient'] = name
    msg = json.dumps(response)
    msg += '\n'
    print(response)
    writer.write(msg.encode())
    await writer.drain()
    if status == ERR:
        return name, False
    else:
        global ALL_USERS
        ALL_USERS[name] = (reader, writer)

        user_list = list(ALL_USERS.keys())

        data = {"type": USERS, 'users':user_list}
        msg = json.dumps(data)
        await broadcast_message(f'{msg}\n')

        welcome = f'Welcome {name}. Send QUIT to disconnect.\n'
        writer.write(welcome.encode())
        await writer.drain()
        return name, True
 

async def disconnect_user(name, writer):
    writer.close()
    await writer.wait_closed()
    global ALL_USERS
    del ALL_USERS[name]

    await broadcast_message(f'{name} has disconnected\n')
 

async def handle_chat_client(reader, writer):
    print('Client connecting...')
    name, status = await authenticate_user(reader, writer)
    print(name, status)
    counter = 2
    if not status:
        while counter > 0:
            await authenticate_user(reader, writer)
            counter -= 1
        return

    try:
        while True:
            msg = await reader.readline()
            data = msg.decode().strip()
            if data['type'] == CHAT_REQUEST:
                
            
    finally:
        await disconnect_user(name, writer)
 
async def main():
    host_address, host_port = '127.0.0.1', 8888
    server = await asyncio.start_server(handle_chat_client, host_address, host_port)
    async with server:
        try:
            print('Chat Server Running\nWaiting for chat clients...')
            await server.serve_forever()
        except ConnectionResetError:
            print("Client disconnected")  

ALL_USERS = {}

asyncio.run(main())