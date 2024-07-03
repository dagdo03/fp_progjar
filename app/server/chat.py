from socket import *
import socket
import threading
import sys
import os
import json
import uuid
import logging
from queue import  Queue
import mysql.connector
from datetime import datetime



# Database connection setup
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="chatapp2"
)

cursor = db.cursor()


class RealmThreadCommunication(threading.Thread):
    def __init__(self, chats, realm_dest_address, realm_dest_port):
        self.chats = chats
        self.chat = {
            'users': {},
            'groups': {}
        }
        self.realm_dest_address = realm_dest_address
        self.realm_dest_port = realm_dest_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.realm_dest_address, self.realm_dest_port))
            threading.Thread.__init__(self)
        except:
            return None

    def sendstring(self, string):
        try:
            self.sock.sendall(string.encode())
            receivedmsg = ""
            while True:
                data = self.sock.recv(32)
                print("diterima dari server", data)
                if (data):
                    receivedmsg = "{}{}" . format(receivedmsg, data.decode())
                    if receivedmsg[-4:]=='\r\n\r\n':
                        print("end of string")
                        return json.loads(receivedmsg)
        except:
            self.sock.close()
            return {'status': 'ERROR', 'message': 'Gagal'}

    def put_private(self, message):
        dest = message['msg_to']
        try:
            self.chat['users'][dest].put(message)
        except KeyError:
            self.chat['users'][dest] = Queue()
            self.chat['users'][dest].put(message)
    
    def put_group(self, message):
        dest = message['msg_to']
        try:
            self.chat['groups'][dest].put(message)
        except KeyError:
            self.chat['groups'][dest] = Queue()
            self.chat['groups'][dest].put(message)

class Chat:
    def __init__(self):
        self.sessions={}
        self.users = {}
        # get all users from database
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        # store users to self.users
        for user in users:
            self.users[user[1]] = {
                'user_id': user[0],
                'nama': user[1],
                'email': user[2],
                'password': user[3],
                'incoming': {},
                'outgoing': {}
            }
        self.groups = {}
        # self.users['messi']={ 'nama': 'Lionel Messi', 'negara': 'Argentina', 'password': 'surabaya', 'incoming' : {}, 'outgoing': {}}
        # self.users['henderson']={ 'nama': 'Jordan Henderson', 'negara': 'Inggris', 'password': 'surabaya', 'incoming': {}, 'outgoing': {}}
        # self.users['lineker']={ 'nama': 'Gary Lineker', 'negara': 'Inggris', 'password': 'surabaya','incoming': {}, 'outgoing':{}}
        # get all groups from database
        cursor.execute("SELECT * FROM chat_groups")
        groups = cursor.fetchall()
        
        # store groups to self.groups
        for group in groups:
            # get group members
            cursor.execute("SELECT * FROM group_members WHERE group_id=%s", (group[0],))
            members_all = cursor.fetchall()

            # store member username to members
            members = [self.get_user_by_id(member[2])['nama'] for member in members_all]

            self.groups[group[1]] = {
                'nama': group[1],
                'password': group[2],
                'members': members,
                'incoming': {},
                'incomingrealm': {}
            }

        self.realms = {}
        self.realms_info = {}

    def proses(self,data):
        j=data.split(" ")
        try:
            command=j[0].strip()
            if (command=='auth'):
                username=j[1].strip()
                password=j[2].strip()
                logging.warning("AUTH: auth {} {}" . format(username,password))
                return self.autentikasi_user(username,password)
            
            elif (command == "users"):
                return self.get_users()
            
            # Fitur Baru Autentikasi
            elif command == "register":
                username = j[1].strip()
                email = j[2].strip()
                password = j[3].strip()
                logging.warning("REGISTER: register {} {}".format(username, password))
                return self.register(username, email, password)
            
            elif (command == "logout"):
                return self.logout()
            
            elif (command=='send'):
                sessionid = j[1].strip()
                usernameto = j[2].strip()
                message=""
                for w in j[3:]:
                    message="{} {}" . format(message,w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SEND: session {} send message from {} to {}" . format(sessionid, usernamefrom,usernameto))
                return self.send_message(sessionid,usernamefrom,usernameto,message)

            elif (command=='inbox'):
                sessionid = j[1].strip()
                username = self.sessions[sessionid]['username']
                username_dest = j[2].strip()
                logging.warning("INBOX: {}" . format(sessionid))
                return self.get_inbox(username, username_dest)
            
            # Local Group-related
            elif (command=='getgroups'):
                return self.get_groups()
            
            elif (command=='addgroup'):
                sessionid = j[1].strip()
                username = self.sessions[sessionid]['username']
                groupname=j[2].strip()
                password=j[3].strip()
                logging.warning("ADDGROUP: session {} username {} addgroup {} {}" . format(sessionid, username, groupname, password))
                return self.add_group(sessionid,username,groupname,password)

            elif (command=='joingroup'):
                sessionid = j[1].strip()
                username = self.sessions[sessionid]['username']
                groupname=j[2].strip()
                password=j[3].strip()
                logging.warning("JOINGROUP: session {} username {} joingroupgroup {} {}" . format(sessionid, username, groupname, password))
                return self.join_group(sessionid,username,groupname,password)

            elif (command=='sendgroup'):
                sessionid = j[1].strip()
                groupname = j[2].strip()
                message=""
                for w in j[3:]:
                    message="{} {}" . format(message,w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SENDGROUP: session {} send message from {} to group {}" . format(sessionid, usernamefrom, groupname))
                return self.send_group(sessionid,usernamefrom,groupname,message)

            elif (command=='inboxgroup'):
                sessionid = j[1].strip()
                groupname = j[2].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("INBOXGROUP: {}" . format(groupname))
                return self.get_inbox_group(sessionid, username, groupname)       

            # Realm-related
            elif (command=='getrealms'):
                return self.get_realms()
            
            elif (command=='addrealm'):
                realm_id = j[1].strip()
                realm_address = j[2].strip()
                realm_port = int(j[3].strip())
                src_address = j[4].strip()
                src_port = int(j[5].strip())
                logging.warning("ADDREALM: {}:{} add realm {} to {}:{}" . format(src_address, src_port, realm_id, realm_address, realm_port))
                return self.add_realm(realm_id, realm_address, realm_port, src_address, src_port)

            elif (command=='ackrealm'):
                realm_id = j[1].strip()
                realm_address = j[2].strip()
                realm_port = int(j[3].strip())
                src_address = j[4].strip()
                src_port = int(j[5].strip())
                logging.warning("ACKREALM: {}:{} received realm {} connection request from {}:{}" . format(realm_address, realm_port, realm_id, src_address, src_port))
                return self.ack_realm(realm_id, realm_address, realm_port, src_address, src_port)

            elif command == 'checkrealm':
                logging.warning("CHECKREALM: {}")
                return self.check_realm()

            elif command == 'sendrealm':
                src_address = j[1].strip()
                src_port = int(j[2].strip())
                sessionid = j[3].strip()
                realm_id = j[4].strip()
                usernameto = j[5].strip()
                message=""
                for w in j[6:]:
                    message="{} {}" . format(message,w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SENDREALM: session {} send realm {} message from {} to {}" . format(sessionid, realm_id, usernamefrom, usernameto))
                return self.send_realm(sessionid,src_address,src_port,realm_id,usernamefrom,usernameto,message)

            elif (command == 'getrealminbox'):
                sessionid = j[1].strip()
                realmid = j[2].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("GETREALMINBOX: {} from realm {}".format(sessionid, realmid))
                return self.get_realm_inbox(username, realmid)
            
            
            elif (command == 'getrealmchat'):
                realmid = j[1].strip()
                username = j[2].strip()
                logging.warning("GETREALMCHAT: from realm {}".format(realmid))
                return self.get_realm_chat(realmid, username)
            
            elif command == 'inboxrealm':
                sessionid = j[1].strip()
                realm_id = j[2].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("INBOXREALM: session {} username {} realm {}" . format(sessionid, username, realm_id))
                return self.get_inbox_realm(sessionid,username,realm_id)
            
            elif command == 'remoteinboxrealm':
                username = j[1].strip()
                realm_id = j[2].strip()
                logging.warning("REMOTEINBOXREALM: username {} realm {}" . format(username, realm_id))
                return self.get_remote_inbox_realm(username,realm_id)

            elif command == 'sendgrouprealm':
                src_address = j[1].strip()
                src_port = int(j[2].strip())
                sessionid = j[3].strip()
                realm_id = j[4].strip()
                groupname = j[5].strip()
                message = ""
                for w in j[6:]:
                    message = "{} {}".format(message, w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SENDGROUPREALM: session {} send message from {} to group {} in realm {}".format(sessionid, usernamefrom, groupname, realm_id))
                return self.send_group_realm(sessionid, src_address, src_port, realm_id, usernamefrom, groupname, message)
            
            elif command == 'recvgrouprealm':
                realm_id = j[1].strip()
                usernamefrom = j[2].strip()
                groupto = j[3].strip()
                message=""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                logging.warning("RECVGROUPREALM: realm {} receive message from {} to group {}" . format(realm_id, usernamefrom, groupto))
                return self.recv_group_realm(realm_id,usernamefrom,groupto,message)
            
            elif command == 'inboxgrouprealm':
                sessionid = j[1].strip()
                realm_id = j[2].strip()
                groupname = j[3].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("INBOXGROUPREALM: session {} username {} groupname {} realm {}" . format(sessionid, username, groupname, realm_id))
                return self.get_inbox_group_realm(sessionid,username,groupname,realm_id)
            
            elif command == 'remoteinboxgrouprealm':
                groupname = j[1].strip()
                realm_id = j[2].strip()
                logging.warning("REMOTEINBOXGROUPREALM: groupname {} realm {}" . format(groupname, realm_id))
                return self.get_remote_inbox_group_realm(groupname,realm_id)
            

            # File-related
            elif (command=='sendfile'):
                sessionid = j[1].strip()
                usernameto = j[2].strip()
                filename = j[3].strip()
                filecontent=""
                for w in j[4:]:
                    filecontent="{} {}" . format(filecontent,w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SENDFILE: session {} send file from {} to {}" . format(sessionid, usernamefrom,usernameto))
                return self.send_file(sessionid,usernamefrom,usernameto,filename,filecontent)
            
            elif (command=='downloadfile'):
                sessionid = j[1].strip()
                fileid = j[2].strip()
                filename = j[3].strip()
                logging.warning("DOWNLOADFILE: {} {}" . format(fileid,filename))
                return self.download_file(sessionid,fileid,filename)
          
            elif (command=='sendgroupfile'):
                sessionid = j[1].strip()
                groupname = j[2].strip()
                filename = j[3].strip()
                filecontent=""
                for w in j[4:]:
                    filecontent="{} {}" . format(filecontent,w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SENDGROUPFILE: session {} send file from {} to {}" . format(sessionid, usernamefrom,groupname))
                return self.send_group_file(sessionid,usernamefrom,groupname,filename,filecontent)
            
            elif (command=='downloadgroupfile'):
                sessionid = j[1].strip()
                groupname = j[2].strip()
                fileid = j[3].strip()
                filename = j[4].strip()
                logging.warning("DOWNLOADGROUPFILE: {} {}" . format(fileid,filename))
                return self.download_group_file(sessionid,groupname,fileid,filename)
       
            elif (command=='sendrealmfile'):
                src_address = j[1].strip()
                src_port = int(j[2].strip())
                sessionid = j[3].strip()
                realm_id = j[4].strip()
                usernameto = j[5].strip()
                filename = j[6].strip()
                filecontent=""
                for w in j[7:]:
                    filecontent="{} {}" . format(filecontent,w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SENDREALMFILE: session {} send file from {} to {}" . format(sessionid, usernamefrom,realm_id))
                return self.send_realm_file(sessionid,src_address,src_port,realm_id,usernamefrom,usernameto,filename,filecontent)
            
            elif (command=='downloadrealmfile'):
                sessionid = j[1].strip()
                realm_id = j[2].strip()
                fileid = j[3].strip()
                filename = j[4].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("DOWNLOADREALMFILE: {} {}" . format(fileid,filename))
                return self.download_realm_file(sessionid,username,realm_id,fileid,filename)
            
            elif command == 'remotedownloadrealmfile':
                username = j[1].strip()
                realm_id = j[2].strip()
                fileid = j[3].strip()
                filename = j[4].strip()
                logging.warning("REMOTEDOWNLOADREALMFILE: username {} realm {}" . format(username, realm_id))
                return self.remote_download_realm_file(username,realm_id,fileid,filename)
            #############
            elif command == 'sendgrouprealmfile':
                src_address = j[1].strip()
                src_port = int(j[2].strip())
                sessionid = j[3].strip()
                realm_id = j[4].strip()
                groupname = j[5].strip()
                filename = j[6].strip()
                filecontent=""
                for w in j[7:]:
                    filecontent="{} {}" . format(filecontent,w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SENDGROUPREALMFILE: session {} send message from {} to group {} in realm {}".format(sessionid, usernamefrom, groupname, realm_id))
                return self.send_group_realm_file(sessionid, src_address, src_port, realm_id, usernamefrom, groupname, filename, filecontent)
            
            elif command == 'recvgrouprealmfile':
                realm_id = j[1].strip()
                usernamefrom = j[2].strip()
                groupto = j[3].strip()
                fileid = j[4].strip()
                filename = j[5].strip()
                filecontent=""
                for w in j[6:]:
                    filecontent="{} {}" . format(filecontent,w)
                logging.warning("RECVGROUPREALMFILE: realm {} receive message from {} to group {}" . format(realm_id, usernamefrom, groupto))
                return self.recv_group_realm_file(realm_id,usernamefrom,groupto,fileid,filename,filecontent)
            
            elif command == 'downloadgrouprealmfile':
                sessionid = j[1].strip()
                realm_id = j[2].strip()
                groupname = j[3].strip()
                fileid = j[4].strip()
                filename = j[5].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("DOWNLOADGROUPREALMFILE: session {} username {} groupname {} realm {}" . format(sessionid, username, groupname, realm_id))
                return self.download_group_realm_file(sessionid,username,groupname,realm_id,fileid,filename)
            
            elif command == 'remotedownloadgrouprealmfile':
                groupname = j[1].strip()
                realm_id = j[2].strip()
                fileid = j[3].strip()
                filename = j[4].strip()
                logging.warning("REMOTEDOWNLOADGROUPREALMFILE: groupname {} realm {}" . format(groupname, realm_id))
                return self.remote_download_group_realm_file(groupname,realm_id,fileid,filename)
            
            
            
            elif command == 'listfile':
                sessionid = j[1].strip()
                logging.warning("LISTFILE: session {}".format(sessionid))
                return self.list_file(sessionid)
            
            elif (command=='listgroupfile'):
                sessionid = j[1].strip()
                groupname = j[2].strip()
                logging.warning("LISTGROUPFILE: session {} list files in group {}" . format(sessionid, groupname))
                return self.list_group_file(sessionid, groupname)
            
            elif (command == 'listrealmfile'):
                sessionid = j[1].strip()
                realmid = j[2].strip()
                logging.warning("LISTREALMFILE: session {} in realm {}".format(sessionid, realmid))
                return self.list_realm_file(sessionid, realmid)

            elif (command == 'listgrouprealmfile'):
                sessionid = j[1].strip()
                groupname = j[2].strip()
                realmid = j[3].strip()
                logging.warning("LISTGROUPREALMFILE: session {} list files in group {} in realm {}".format(sessionid, groupname, realmid))
                return self.list_group_realm_file(sessionid, groupname, realmid)


        except KeyError:
            return { 'status': 'ERROR', 'message' : 'Informasi tidak ditemukan'}
        except IndexError:
            return {'status': 'ERROR', 'message': '--Protocol Tidak Benar'}

    def autentikasi_user(self,username,password):
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone() 
        if (username not in user[1]):
            return { 'status': 'ERROR', 'message': 'User Tidak Ada' }
        if (password != user[3]):
            return { 'status': 'ERROR', 'message': 'Password Salah' }
        tokenid = str(uuid.uuid4()) 
        self.users[username] = {"user_id": user[0], "nama": user[1], "email": user[2], "password": user[3], "incoming": {}, "outgoing": {}}
        self.sessions[tokenid]={ 'username': username, 'userdetail':self.users[username]}
        return { 'status': 'OK', 'tokenid': tokenid }

    def get_users(self):
        # get all users from database
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        print("users: ", users)
        print("self users: ", self.users)
        # if users not exist in self.users
        for user in users:
            print("user: ", user)
            if user[1] not in self.users:
                print("MASUKKKKK")
                self.users[user[1]] = {
                    'user_id': user[0],
                    'nama': user[1],
                    'email': user[2],
                    'password': user[3],
                    'incoming': {},
                    'outgoing': {}
                }
        return {"status": "OK", "message": self.users}

    # FITUR AUTENTIKASI BARU
    def register(self, username, email, password):
        username = username.replace("-", " ")
        if username in self.users:
            return {"status": "ERROR", "message": "User Sudah Terdaftar"}
        # self.users[username] = {"nama": nama, "negara": negara, "password": password, "incoming": {}, "outgoing": {}}
        cursor.execute("INSERT INTO users (username, email, password_hash, created_at) VALUES (%s, %s, %s, %s)", (username, email, password, datetime.now()))
        db.commit()

        # get user data from database
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        print("user: ", user)
        self.users[username] = {"user_id": user[0], "nama": user[1], "email": user[2], "password": user[3], "incoming": {}, "outgoing": {}}


        tokenid = str(uuid.uuid4())
        self.sessions[tokenid]={ 'username': username, 'userdetail':self.users[username]}
        return {"status": "OK", "tokenid": tokenid}
    
    def logout(self, tokenid):
        if tokenid in self.sessions:
            del self.sessions[tokenid]
            return {"status": "OK"}
        else:
            return {"status": "ERROR", "message": "User Belum Login"}
    
    
    def get_user(self,username):
        # check if user is exist in database
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if (user == None):
            return False
        # add user to self.users
        if user[1] not in self.users:
            self.users[user[1]] = {"user_id": user[0], "nama": user[1], "email": user[2], "password": user[3], "incoming": {}, "outgoing": {}}
        return self.users[user[1]]
    
    def get_user_by_id(self, user_id):
        # get user data from database
        cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        user = cursor.fetchone()
        if (user == None):
            return False
        # add user to self.users
        if user[1] not in self.users:
            self.users[user[1]] = {"user_id": user[0], "nama": user[1], "email": user[2], "password": user[3], "incoming": {}, "outgoing": {}}
        return self.users[user[1]]

    def send_message(self,sessionid,username_from,username_dest,message):
        # get user data from username_dest
        cursor.execute("SELECT * FROM users WHERE username=%s", (username_dest,))
        user_dest = cursor.fetchone()
        # if user_dest not exist in database
        if (user_dest == None):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        
        # if user_dest not exist in self.users
        if (username_dest not in self.users):
            self.users[username_dest] = {"user_id": user_dest[0], "nama": user_dest[1], "email": user_dest[2], "password": user_dest[3], "incoming": {}, "outgoing": {}}
        
        # check if sessionid is valid
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)
        

        if (s_fr==False or s_to==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        
        # store chat to chats table
        cursor.execute("INSERT INTO chats (message, sender_id, receiver_id, created_at) VALUES (%s, %s, %s, %s)", (message, s_fr['user_id'], s_to['user_id'], datetime.now()))
        # commit the changes
        db.commit()


        message = { 'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
        outqueue_sender = s_fr['outgoing']
        inqueue_receiver = s_to['incoming']
        try:	
            outqueue_sender[username_from].append(message)
        except KeyError:
            outqueue_sender[username_from]=list()
            outqueue_sender[username_from].append(message)
        try:
            inqueue_receiver[username_from].append(message)
        except KeyError:
            inqueue_receiver[username_from]=list()
            inqueue_receiver[username_from].append(message)
        return {'status': 'OK', 'message': 'Message Sent'}

    def get_inbox(self,username, username_dest):
        # check if user is exist in database
        cursor.execute("SELECT * FROM users WHERE username=%s", (username_dest,))
        user_dest = cursor.fetchone()
        if (user_dest == None):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        
        # check if user is exist in self.users
        
        if (username_dest not in self.users):
            self.users[username_dest] = {"user_id": user_dest[0], "nama": user_dest[1], "email": user_dest[2], "password": user_dest[3], "incoming": {}, "outgoing": {}}
        
        s_fr = self.get_user(username)
        s_to = self.get_user(username_dest)
        

        if (s_fr==False or s_to==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}

        # get chat data from database
        cursor.execute("SELECT * FROM chats WHERE (sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s)", (s_fr['user_id'], s_to['user_id'], s_to['user_id'], s_fr['user_id']))

        chats = cursor.fetchall()
        print("chats: ", chats)

        msgs = []
        for chat in chats:
            print("chat coyyyyy: ", chat)
            sender = self.get_user_by_id(chat[2])
            receiver = self.get_user_by_id(chat[3])
            # format date to string
            chat_date = chat[4].strftime("%Y-%m-%d %H:%M:%S")
            # change chat date to string
            chat_data_str = str(chat_date)
            msgs.append({
                'msg_from': sender['nama'],
                'msg_to': receiver['nama'],
                'msg': chat[1],
                'created_at': chat_date
            })
        # incoming = s_fr['incoming']
        # msgs={}
        # for users in incoming:
        #     msgs[users]=[]
        #     temp_queue = incoming[users].queue.copy()
        #     while len(temp_queue) > 0:
        #         msgs[users].append(temp_queue.pop())

        return {'status': 'OK', 'messages': msgs}
    
    def get_group(self,groupname):
        if (groupname not in self.groups):
            return False
        return self.groups[groupname]
    
    def get_groups(self):
        # get all groups from database
        cursor.execute("SELECT * FROM chat_groups")
        groups = cursor.fetchall()
        print("groups: ", groups)

        # if groups not exist in self.groups
        for group in groups:
            # get group members
            cursor.execute("SELECT * FROM group_members WHERE group_id=%s", (group[0],))
            members_all = cursor.fetchall()
            print("members_all: ", members_all)
            
            print("group get: ", self.groups)
            # store member username to members
            members = [self.get_user_by_id(member[2])['nama'] for member in members_all]

            if group[1] not in self.groups:
                self.groups[group[1]] = {
                    'nama': group[1],
                    'password': group[2],
                    'members': members,
                    'incoming': {},
                    'incomingrealm': {}
                }
                print("self.groups: ", self.groups)

        return {"status": "OK", "message": self.groups}    
    
    def add_group(self,sessionid,username,groupname,password):
        # check if groupname already exist
        cursor.execute("SELECT * FROM chat_groups WHERE group_name=%s", (groupname,))
        group = cursor.fetchone()
        if (group != None):
            return { 'status': 'ERROR', 'message': 'Group sudah ada' }

        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (groupname in self.groups):
            return { 'status': 'ERROR', 'message': 'Group sudah ada' }
        
        # store group to database
        cursor.execute("INSERT INTO chat_groups (group_name, created_at, password) VALUES (%s, %s, %s)", (groupname, datetime.now(), password))
        
        # store group members to database
        cursor.execute("SELECT * FROM chat_groups WHERE group_name=%s", (groupname,))
        group = cursor.fetchone()

        cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)", (group[0], self.users[username]['user_id']))
        db.commit()

        self.groups[groupname]={
            'nama': groupname,
            'password': password,
            'incoming' : {},
            'members' : [],
            'incomingrealm' : {}
        }

        self.groups[groupname]['members'].append(username)
        return { 'status': 'OK', 'message': 'Add group berhasil' }
    
    def join_group(self,sessionid,username,groupname,password):
        # check if groupname does not exist in database
        cursor.execute("SELECT * FROM chat_groups WHERE group_name=%s", (groupname,))
        group = cursor.fetchone()
        if (group == None):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        
        # check if password is wrong
        if (group[2] != password):
            return { 'status': 'ERROR', 'message': 'Password Salah' }
        
        # check if user already join the group
        cursor.execute("SELECT * FROM group_members WHERE group_id=%s AND user_id=%s", (group[0], self.users[username]['user_id']))
        member = cursor.fetchone()
        if (member != None):
            return { 'status': 'ERROR', 'message': 'User sudah join' }
        
        # store group members to database
        cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)", (group[0], self.users[username]['user_id']))
        db.commit()

        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (groupname not in self.groups):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        if (self.groups[groupname]['password']!= password):
            return { 'status': 'ERROR', 'message': 'Password Salah' }
        if (username in self.groups[groupname]['members']):
            return { 'status': 'ERROR', 'message': 'User sudah join' }
        self.groups[groupname]['members'].append(username)
        return { 'status': 'OK', 'message': 'Join group berhasil' }
    
    def send_group(self,sessionid,username_from,group_dest,message):
        # check if groupname does not exist in database
        cursor.execute("SELECT * FROM chat_groups WHERE group_name=%s", (group_dest,))
        group = cursor.fetchone()
        if (group == None):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        
        # check if user is not a member of the group
        cursor.execute("SELECT * FROM group_members WHERE group_id=%s AND user_id=%s", (group[0], self.users[username_from]['user_id']))
        member = cursor.fetchone()
        if (member == None):
            return { 'status': 'ERROR', 'message': 'Bukan member group' }
    

        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (group_dest not in self.groups):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        if (username_from not in self.groups[group_dest]['members']):
            return { 'status': 'ERROR', 'message': 'Bukan member group' }
        s_fr = self.get_user(username_from)
        g_to = self.get_group(group_dest)
        

        if (s_fr==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        if (g_to==False):
            return {'status': 'ERROR', 'message': 'Group Tidak Ditemukan'}
        
        # store chat to group_chats table with group_id
        cursor.execute("INSERT INTO group_chats (group_id, sender_id, message, created_at) VALUES (%s, %s, %s, %s)", (group[0], s_fr['user_id'], message, datetime.now()))
        db.commit()

        message = { 'msg_from': s_fr['nama'], 'msg_ufrom': username_from, 'msg_to': g_to['nama'], 'msg': message }
        outqueue_sender = s_fr['outgoing']
        inqueue_receiver = g_to['incoming']
        try:
            outqueue_sender[username_from].append(message)
        except KeyError:
            outqueue_sender[username_from]=list()
            outqueue_sender[username_from].append(message)
        try:
            inqueue_receiver[username_from].append(message)
        except KeyError:
            inqueue_receiver[username_from]=list()
            inqueue_receiver[username_from].append(message)
        return {'status': 'OK', 'message': 'Message Sent'}

    def get_inbox_group(self,sessionid, username, groupname):
        # check if groupname does not exist in database
        cursor.execute("SELECT * FROM chat_groups WHERE group_name=%s", (groupname,))
        group = cursor.fetchone()
        if (group == None):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        
        # check if user is not a member of the group
        cursor.execute("SELECT * FROM group_members WHERE group_id=%s AND user_id=%s", (group[0], self.users[username]['user_id']))
        member = cursor.fetchone()
        if (member == None):
            return { 'status': 'ERROR', 'message': 'Bukan member group' }
        
        # get chat data from database
        cursor.execute("SELECT * FROM group_chats WHERE group_id=%s", (group[0],))
        chats = cursor.fetchall()
        print("chats: ", chats)

        msgs = []

        for chat in chats:
            sender = self.get_user_by_id(chat[2])
            # format date to string
            print("chat data: ", chat)
            chat_date = chat[4].strftime("%Y-%m-%d %H:%M:%S")
            msgs.append({
                'msg_from': sender['nama'],
                'msg_to': groupname,
                'msg': chat[3],
                'created_at': chat_date
            })

        # if (sessionid not in self.sessions):
        #     return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        # if (groupname not in self.groups):
        #     return { 'status': 'ERROR', 'message': 'Group belum ada' }
        # if (username not in self.groups[groupname]['members']):
        #     return { 'status': 'ERROR', 'message': 'Bukan member group' }
        # s_fr = self.get_group(groupname)
        # incoming = s_fr['incoming']
        # msgs={}
        # for users in incoming:
        #     msgs[users]=[]
        #     temp_queue = incoming[users].queue.copy()
        #     while len(temp_queue) > 0:
        #         msgs[users].append(temp_queue.pop())

        return {'status': 'OK', 'messages': msgs}

    def add_realm(self,realm_id,realm_address,realm_port,src_address,src_port):
        if (realm_id in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm sudah ada' }
        try:
            self.realms[realm_id] = RealmThreadCommunication(self, realm_address, realm_port)
            result = self.realms[realm_id].sendstring("ackrealm {} {} {} {} {}\r\n" . format(realm_id, realm_address, realm_port, src_address, src_port))
            if result['status']=='OK':
                self.realms_info[realm_id] = {'serverip': realm_address, 'port': realm_port}
                return result
            else:
                return {'status': 'ERROR', 'message': 'Realm unreachable'}
        except:
            return {'status': 'ERROR', 'message': 'Realm unreachable'}
   
    def ack_realm(self,realm_id,realm_address,realm_port,src_address,src_port):
        self.realms[realm_id] = RealmThreadCommunication(self, src_address, src_port)
        self.realms_info[realm_id] = {'serverip': src_address, 'port': src_port}
        return { 'status': 'OK', 'message': 'Connect realm berhasil' }

    def check_realm(self):
        return { 'status': 'OK', 'message': self.realms_info }

    def send_realm(self,sessionid,src_realm_addr,src_realm_port,realm_id,username_from,username_to,message):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_to)
        if (s_fr==False or s_to==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        message_to_put = { 'msg_from': s_fr['nama'] + "(" + src_realm_addr + ":" + str(src_realm_port) + ")", 'msg_to': s_to['nama'], 'msg': message }
        self.realms[realm_id].put_private(message_to_put)
        return {'status': 'OK', 'message': 'Pesan realm dikirim'}

    def get_inbox_realm(self,sessionid,username,realm_id):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        return self.realms[realm_id].sendstring("remoteinboxrealm {} {}\r\n".format(username, realm_id))
    
    def get_remote_inbox_realm(self,username,realm_id):
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        s_fr = self.get_user(username)
        msgs=[]
        temp_queue = self.realms[realm_id].chat['users'][s_fr['nama']].queue.copy()
        while len(temp_queue) > 0:
            msgs.append(temp_queue.pop())
        return {'status': 'OK', 'messages': msgs}

    # Group chat across realms
    def send_group_realm(self, sessionid, src_realm_addr, src_realm_port, realm_id, username_from, groupname, message):
        if sessionid not in self.sessions:
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if realm_id not in self.realms_info:
            return {'status': 'ERROR', 'message': 'Realm belum ada'}
        
        group = self.groups[groupname]
        if username_from not in group['members']:
            return {'status': 'ERROR', 'message': 'Bukan member group'}

        s_fr = self.get_user(username_from)
        g_to = self.get_group(groupname)
        if (s_fr==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        if (g_to==False):
            return {'status': 'ERROR', 'message': 'Grup Tidak Ditemukan'}
        
        message_to_put = {'msg_from': s_fr['nama'] + "(" + src_realm_addr + ":" + str(src_realm_port) + ")", 'msg_to': g_to['nama'], 'msg': message}
        self.realms[realm_id].put_group(message_to_put)

        return self.realms[realm_id].sendstring("recvgrouprealm {} {} {} {}\r\n" . format(realm_id, username_from, groupname, message))
    
    def recv_group_realm(self, realm_id, username_from, groupname, message):
        if (realm_id not in self.realms):
            return {'status': 'ERROR', 'message': 'Realm belum ada'}
        s_fr = self.get_user(username_from)
        g_to = self.get_group(groupname)
        if (s_fr==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        if (g_to==False):
            return {'status': 'ERROR', 'message': 'Grup Tidak Ditemukan'}

        src_realm_addr = self.realms_info[realm_id]['serverip']
        src_realm_port = self.realms_info[realm_id]['port']
        
        try:
            message_to_put = {'msg_from': s_fr['nama'] + "(" + src_realm_addr + ":" + str(src_realm_port) + ")", 'msg_to': g_to['nama'], 'msg': message}
            self.realms[realm_id].put_group(message_to_put)
            return {'status': 'OK', 'message': 'Pesan grup realm terkirim'}
        except:
            return {'status': 'ERROR', 'message': 'Pesan grup realm gagal terkirim'}
    
    def get_inbox_group_realm(self,sessionid,username,groupname,realm_id):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (groupname not in self.groups):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        if (username not in self.groups[groupname]['members']):
            return { 'status': 'ERROR', 'message': 'Bukan member group' }
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        return self.realms[realm_id].sendstring("remoteinboxgrouprealm {} {}\r\n".format(groupname, realm_id))
    
    def get_remote_inbox_group_realm(self,groupname,realm_id):
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        s_fr = self.get_group(groupname)
        incoming = s_fr['incoming']
        # print("s_fr is: {}" . format(s_fr))
        # print(incoming)
        
        msgs=[]
        temp_queue = self.realms[realm_id].chat['groups'][s_fr['nama']].queue.copy()
        while len(temp_queue) > 0:
            msgs.append(temp_queue.pop())
        return {'status': 'OK', 'messages': msgs}
    
    def send_file(self,sessionid,username_from,username_dest,filename,filecontent):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)

        if (s_fr==False or s_to==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}

        file_id_ = str(uuid.uuid4())
        message = { 'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'fileid': file_id_, 'filename': filename, 'filecontent':filecontent }
        outqueue_sender = s_fr['outgoing']
        inqueue_receiver = s_to['incoming']
        try:
            outqueue_sender[username_from].put(message)
        except KeyError:
            outqueue_sender[username_from]=Queue()
            outqueue_sender[username_from].put(message)
        try:
            inqueue_receiver[username_from].put(message)
        except KeyError:
            inqueue_receiver[username_from]=Queue()
            inqueue_receiver[username_from].put(message)
        return {'status': 'OK', 'message': 'File Sent', 'file_id': file_id_ }
    
    def download_file(self,sessionid,fileid,filename):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        username = self.sessions[sessionid]['username']
        s_fr = self.get_user(username)
        incoming = s_fr['incoming']
        print("incominggggg", incoming)
        filecontent=""
        for users in incoming:
            temp_queue = incoming[users].queue.copy()
            while len(temp_queue) > 0:
                msg = temp_queue.pop()
                print("MSG: {}". format(msg))
                if 'fileid' in msg and msg['fileid']==fileid:
                    return {'status': 'OK', 'message': msg['filecontent']}
        return {'status': 'ERROR', 'message': 'File tidak ditemukan'}
    
    def send_group_file(self,sessionid,username_from,group_dest,filename,filecontent):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (group_dest not in self.groups):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        if (username_from not in self.groups[group_dest]['members']):
            return { 'status': 'ERROR', 'message': 'Bukan member group' }
        s_fr = self.get_user(username_from)
        g_to = self.get_group(group_dest)

        if (s_fr==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        if (g_to==False):
            return {'status': 'ERROR', 'message': 'Group Tidak Ditemukan'}

        message = { 'msg_from': s_fr['nama'], 'msg_to': g_to['nama'], 'fileid': str(uuid.uuid4()), 'filename': filename, 'filecontent':filecontent }
        outqueue_sender = s_fr['outgoing']
        inqueue_receiver = g_to['incoming']
        try:
            outqueue_sender[username_from].put(message)
        except KeyError:
            outqueue_sender[username_from]=Queue()
            outqueue_sender[username_from].put(message)
        try:
            inqueue_receiver[username_from].put(message)
        except KeyError:
            inqueue_receiver[username_from]=Queue()
            inqueue_receiver[username_from].put(message)
        return {'status': 'OK', 'message': 'Group File Sent'}
    
    def download_group_file(self,sessionid,groupname,fileid,filename):
        username = self.sessions[sessionid]['username']
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (groupname not in self.groups):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        if (username not in self.groups[groupname]['members']):
            return { 'status': 'ERROR', 'message': 'Bukan member group' }
        s_fr = self.get_group(groupname)
        incoming = s_fr['incoming']
        filecontent=""
        for users in incoming:
            temp_queue = incoming[users].queue.copy()
            while len(temp_queue) > 0:
                msg = temp_queue.pop()
                print("MSG: {}". format(msg))
                if 'fileid' in msg and msg['fileid']==fileid:
                    return {'status': 'OK', 'message': msg['filecontent']}
        return {'status': 'ERROR', 'message': 'File tidak ditemukan'}
    
    def send_realm_file(self,sessionid,src_realm_addr,src_realm_port,realm_id,username_from,username_to,filename,filecontent):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_to)
        if (s_fr==False or s_to==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        
        file_id_ = str(uuid.uuid4())
        
        message_to_put = { 'msg_from': s_fr['nama'] + "(" + src_realm_addr + ":" + str(src_realm_port) + ")", 'msg_to': s_to['nama'], 'fileid': file_id_, 'filename': filename, 'filecontent':filecontent }
        self.realms[realm_id].put_private(message_to_put)
        return {'status': 'OK', 'message': 'Pesan realm dikirim', 'file_id': file_id_}

    def download_realm_file(self,sessionid,username,realm_id,fileid,filename):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        return self.realms[realm_id].sendstring("remotedownloadrealmfile {} {} {} {}\r\n".format(username, realm_id,fileid,filename))
    
    def remote_download_realm_file(self,username,realm_id,fileid,filename):
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        s_fr = self.get_user(username)
        
        temp_queue = self.realms[realm_id].chat['users'][s_fr['nama']].queue.copy()
        while len(temp_queue) > 0:
            msg = temp_queue.pop()
            print("MSG: {}". format(msg))
            if 'fileid' in msg and msg['fileid']==fileid:
                return {'status': 'OK', 'message': msg['filecontent']}
        return {'status': 'ERROR', 'message': 'File tidak ditemukan'}
    
    def send_group_realm_file(self, sessionid, src_realm_addr, src_realm_port, realm_id, username_from, groupname, filename, filecontent):
        if sessionid not in self.sessions:
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if realm_id not in self.realms_info:
            return {'status': 'ERROR', 'message': 'Realm belum ada'}
        
        group = self.groups[groupname]
        if username_from not in group['members']:
            return {'status': 'ERROR', 'message': 'Bukan member group'}

        s_fr = self.get_user(username_from)
        g_to = self.get_group(groupname)
        if (s_fr==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        if (g_to==False):
            return {'status': 'ERROR', 'message': 'Grup Tidak Ditemukan'}
        fileid = str(uuid.uuid4())
        message_to_put = {'msg_from': s_fr['nama'] + "(" + src_realm_addr + ":" + str(src_realm_port) + ")", 'msg_to': g_to['nama'], 'fileid': fileid, 'filename': filename, 'filecontent':filecontent}
        self.realms[realm_id].put_group(message_to_put)

        return self.realms[realm_id].sendstring("recvgrouprealmfile {} {} {} {} {} {}\r\n" . format(realm_id, username_from, groupname, fileid, filename, filecontent))
    
    def recv_group_realm_file(self, realm_id, username_from, groupname, fileid, filename, filecontent):
        if (realm_id not in self.realms):
            return {'status': 'ERROR', 'message': 'Realm belum ada'}
        s_fr = self.get_user(username_from)
        g_to = self.get_group(groupname)
        if (s_fr==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        if (g_to==False):
            return {'status': 'ERROR', 'message': 'Grup Tidak Ditemukan'}

        src_realm_addr = self.realms_info[realm_id]['serverip']
        src_realm_port = self.realms_info[realm_id]['port']
        
        try:
            message_to_put = {'msg_from': s_fr['nama'] + "(" + src_realm_addr + ":" + str(src_realm_port) + ")", 'msg_to': g_to['nama'], 'fileid': fileid, 'filename': filename, 'filecontent':filecontent}
            self.realms[realm_id].put_group(message_to_put)
            return {'status': 'OK', 'message': 'File grup realm terkirim'}
        except:
            return {'status': 'ERROR', 'message': 'File grup realm gagal terkirim'}
    
    def download_group_realm_file(self,sessionid,username,groupname,realm_id,fileid, filename):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (groupname not in self.groups):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        if (username not in self.groups[groupname]['members']):
            return { 'status': 'ERROR', 'message': 'Bukan member group' }
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        return self.realms[realm_id].sendstring("remotedownloadgrouprealmfile {} {} {} {}\r\n".format(groupname, realm_id, fileid, filename))
    
    def remote_download_group_realm_file(self,groupname,realm_id,fileid,filename):
        if (realm_id not in self.realms_info):
            return { 'status': 'ERROR', 'message': 'Realm belum ada' }
        s_fr = self.get_group(groupname)
        incoming = s_fr['incoming']
        # print("s_fr is: {}" . format(s_fr))
        # print(incoming)
        
        temp_queue = self.realms[realm_id].chat['groups'][s_fr['nama']].queue.copy()
        while len(temp_queue) > 0:
            msg = temp_queue.pop()
            print("MSG: {}". format(msg))
            if 'fileid' in msg and msg['fileid']==fileid:
                return {'status': 'OK', 'message': msg['filecontent']}
        return {'status': 'ERROR', 'message': 'File tidak ditemukan'}
        
        # filecontent=""
        # temp_queue = self.realms[realm_id].chat['groups'][s_fr['nama']].queue.copy()
        # while len(temp_queue) > 0:
        #     msg = temp_queue.pop()
        #     print("MSG: {}". format(msg))
        #     if 'fileid' in msg and msg['fileid']==fileid:
        #         return {'status': 'OK', 'message': msg['filecontent']}
        # return {'status': 'ERROR', 'message': 'File tidak ditemukan'}
    
    
    def get_realms(self):
        return {"status": "OK", "message": self.realms}
    
# ========================= LIST FILE PROTOCOL =========================
    def list_file(self, sessionid):
        if sessionid not in self.sessions:
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        
        username = self.sessions[sessionid]['username']
        user = self.get_user(username)
        
        if not user:
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        
        incoming = user['incoming']
        file_list = []

        for sender in incoming:
            temp_queue = list(incoming[sender].queue)
            for msg in temp_queue:
                if 'fileid' in msg:
                    file_list.append({
                        'fileid': msg['fileid'],
                        'filename': msg['filename'],
                        'from': msg['msg_from']
                    })

        return {'status': 'OK', 'files': file_list}

    def list_group_file(self, sessionid, groupname):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (groupname not in self.groups):
            return { 'status': 'ERROR', 'message': 'Group belum ada' }
        username = self.sessions[sessionid]['username']
        if (username not in self.groups[groupname]['members']):
            return { 'status': 'ERROR', 'message': 'Bukan member group' }
        group = self.get_group(groupname)
        incoming = group['incoming']
        file_list = []
        for users in incoming:
            temp_queue = incoming[users].queue.copy()
            while len(temp_queue) > 0:
                msg = temp_queue.pop()
                if 'fileid' in msg:
                    file_list.append({'from': msg['msg_from'], 'filename': msg['filename'], 'fileid': msg['fileid']})
        return {'status': 'OK', 'files': file_list}

    def list_realm_file(self, sessionid, realmid):
        if sessionid not in self.sessions:
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        
        if realmid not in self.realms_info:
            return {'status': 'ERROR', 'message': 'Realm belum ada'}
        
        username = self.sessions[sessionid]['username']
        user = self.get_user(username)
        
        if not user:
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        
        if realmid not in self.realms:
            return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
        
        incoming = self.realms[realmid].chat['users'][username].queue.copy()
        file_list = []

        while len(incoming) > 0:
            msg = incoming.pop()
            if 'fileid' in msg:
                file_list.append({
                    'fileid': msg['fileid'],
                    'filename': msg['filename'],
                    'from': msg['msg_from']
                })

        return {'status': 'OK', 'files': file_list}

    def list_group_realm_file(self, sessionid, groupname, realmid):
        if sessionid not in self.sessions:
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        
        if realmid not in self.realms_info:
            return {'status': 'ERROR', 'message': 'Realm belum ada'}
        
        if groupname not in self.groups:
            return {'status': 'ERROR', 'message': 'Group belum ada'}
        
        username = self.sessions[sessionid]['username']
        if username not in self.groups[groupname]['members']:
            return {'status': 'ERROR', 'message': 'Bukan member group'}
        
        if realmid not in self.realms:
            return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
        
        incoming = self.realms[realmid].chat['groups'][groupname].queue.copy()
        file_list = []

        while len(incoming) > 0:
            msg = incoming.pop()
            if 'fileid' in msg:
                file_list.append({
                    'fileid': msg['fileid'],
                    'filename': msg['filename'],
                    'from': msg['msg_from']
                })

        return {'status': 'OK', 'files': file_list}
    