import socket
import asyncio
import json
import aiosqlite
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from constants import *

ph = PasswordHasher()


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
        return name, True
 

async def disconnect_user(name, writer):
    writer.close()
    await writer.wait_closed()
    global ALL_USERS
    del ALL_USERS[name]
 
async def send_one_one_message(writer, type, message, fro, to):
    msg = {
        'type':type,
        'message': message,
        'from': fro,
        'to': to
    }
    msg_str = json.dumps(msg)
    msg_str += '\n'
    msg_bytes = msg_str.encode()
    print(f'Sending: {msg_str}')
    writer.write(msg_bytes)
    await writer.drain()

async def multicast_message(writers, type, message, fro, tos, grp_id):
    msg = {
    'type':type,
    'message': message,
    'from': fro,
    'group_id': grp_id
    }
    for i in range(len(writers)):
        writer = writers[i]
        msg['to'] = tos[i]
        msg_str = json.dumps(msg)
        msg_str += '\n'
        msg_bytes = msg_str.encode()
        print(f'Sending: {msg_str}')
        writer.write(msg_bytes)
        await writer.drain()
        
async def send_file_pvt(writer, file, filename, fro, to):
    msg = {
        'type': FILE_RECV_PVT,
        'file': file,
        'file_name': filename,
        'from': fro,
        'to': to
    }
    msg_str = json.dumps(msg)
    msg_str += '\n'
    msg_bytes = msg_str.encode()
    # print(f'Sending: {msg_str}')
    writer.write(msg_bytes)
    await writer.drain()
    pass
async def send_file_grp(writers, file, filename, fro, tos, grp_id):
    msg = {
        'type': FILE_RECV_GRP,
        'file': file,
        'file_name': filename,
        'from': fro,
        'group_id': grp_id
    }
    for i in range(len(writers)):
        writer = writers[i]
        msg['to'] = tos[i]
        msg_str = json.dumps(msg)
        msg_str += '\n'
        msg_bytes = msg_str.encode()
        print(f'Sending: {msg_str}')
        writer.write(msg_bytes)
        await writer.drain()
    
async def handle_chat_client(reader, writer):
    print('Client connecting...')
    name, status = await authenticate_user(reader, writer)
    # print(name, status)
    counter = 2
    if not status:
        while counter > 0:
            await authenticate_user(reader, writer)
            counter -= 1
        return
    recipient = None
    group = None
    # print(ALL_USERS)
    try:
        while True:
            try:
                msg = await reader.readline()
                data = msg.decode().strip()
                data = json.loads(data)
                print(name, data)
                
                if data['type'] == REQ_ACC:
                    recipient = data['to']
                    await send_one_one_message(ALL_USERS[recipient][1], REQ_ACC, "Request accepted", name, recipient)
                elif data['type'] == REQ_DEN:
                    pass
                elif data['type'] == CHAT_REQUEST:
                    recipient = data['username']
                    if recipient not in ALL_USERS:
                        await send_one_one_message(writer, INVALID_USER, f"User {recipient} not found", name, recipient)
                        recipient = None
                        continue
                    else:
                        await send_one_one_message(ALL_USERS[recipient][1], CHAT_REQUEST,f"Chat request from {name}", name, recipient)
                
                elif data['type'] == GROUP_REQ:
                    group = data['group_id']
                    ALL_GROUPS[group] = [name]
                    tos = data['users']
                    group_members = []
                    print('tos', tos)
                    print(ALL_USERS.keys())
                    for to in tos:
                        if to not in ALL_USERS:
                            print(to, ALL_USERS.keys())
                            await send_one_one_message(writer, INVALID_USER, f"User {to} not found", name, to)
                            
                        else:
                            group_members.append(to)
                            await multicast_message([ALL_USERS[to][1] for to in group_members], 
                                                    GROUP_REQ, f"Group request from {name}", name, group_members, group)
                
                elif data['type'] == FILE_SEND_GRP:
                    file_data = data['file']
                    file_name = data['file_name']
                    group_members = filter(lambda x: x != name, ALL_GROUPS[group])
                    await send_file_grp([ALL_USERS[to][1] for to in group_members], file_data, file_name, name, group_members, group)
                elif data['type'] == FILE_SEND_PVT:
                    file_data = data['file']
                    file_name = data['file_name']
                    to = recipient
                    await send_file_pvt(ALL_USERS[to][1], file_data, file_name, name, to)
                elif data['type'] == GROUP_REQ_ACC:
                    group_id = data['group_id']
                    group = group_id
                    ALL_GROUPS[group_id].append(name)
                    group_members = ALL_GROUPS[group_id]
                    await multicast_message([ALL_USERS[to][1] for to in group_members],
                                             GROUP_REQ_ACC, f"Group request accepted by {name}", name, group_members, group_id)
                elif data['type'] == GROUP_CHAT:
                    group_id = data['group_id']
                    group = group_id
                    group_members = ALL_GROUPS[group_id]
                    await multicast_message([ALL_USERS[to][1] for to in group_members],
                                             GROUP_CHAT, f"{data['message']}", name, group_members, group_id)
                elif data['type'] == CHAT:
                    await send_one_one_message(ALL_USERS[recipient][1], CHAT, data['message'], name, recipient)
                elif data['type'] == DISCONNECT:
                    pass
            except json.decoder.JSONDecodeError:
                print(name, "diconnected")
                break
                
            
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
ALL_GROUPS = {} # groupname: members
asyncio.run(main())