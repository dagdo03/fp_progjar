import socket
import os
import json
import sys
import ntpath
import base64
import threading

TARGET_IP = os.getenv("SERVER_IP") or "127.0.0.1"
TARGET_PORT = os.getenv("SERVER_PORT") or "8889"


class ChatClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(TARGET_IP)
        print(TARGET_PORT)
        self.server_address = (TARGET_IP,int(TARGET_PORT))
        self.sock.connect(self.server_address)
        self.sock2.connect(self.server_address)
        self.tokenid=""
        self.username = ""
        self.groups = {}
        self.address_ip = TARGET_IP
        self.address_port = TARGET_PORT
        self.listener_thread = threading.Thread(target=self.receive_messages, daemon=True)
        self.listener_thread.start()

    def proses(self,cmdline):
        j=cmdline.split(" ")
        try:
            command=j[0].strip()
            if (command=='auth'):
                username=j[1].strip()
                password=j[2].strip()
                return self.login(username,password)
            elif (command=='send'):
                usernameto = j[1].strip()
                message=""
                for w in j[2:]:
                   message="{} {}" . format(message,w)
                return self.sendmessage(usernameto,message)
            elif (command=='inbox'):
                username_from = j[1].strip()
                return self.inbox(username_from)

            elif (command=="users"):
                return self.get_users()
            
            elif (command == "register"):
                username = j[1].strip()
                email = j[2].strip()
                password = j[3].strip()
                print(username, email, password)

                return self.register(username, email, password)
            elif (command=='logout'):
                pass
            
            elif (command == "group"):
                print(j)
                if(j[1].strip() == 'get'):
                    return self.getgroups()
                elif(j[1].strip() == "add"):
                    print(j)
                    groupname=j[2].strip()
                    password=j[3].strip()
                    self.groups[groupname]={
                        'nama': groupname,
                        'password': password,
                        'members' : [],
                        'incoming' : {},
                        'incomingrealm' : {}
                    }
                    return self.addgroup(groupname, password)
                elif(j[1].strip() == "join"):
                    groupname=j[2].strip()
                    password=j[3].strip()
                    return self.joingroup(groupname, password)
                elif(j[1].strip() == "inbox"):
                    groupname=j[2].strip()
                    return self.inboxgroup(groupname)
                elif(j[1].strip() == "send"):
                    groupname=j[2].strip()
                    message=""
                    for w in j[3:]:
                        message="{} {}" . format(message,w)
                    return self.sendgroup(groupname, message)
                
                
            elif (command=='addrealm'):
                realm_id=j[1].strip()
                realm_address=j[2].strip()
                realm_port=j[3].strip()
                return self.addrealm(realm_id,realm_address,realm_port)
                
            elif (command=='checkrealm'):
                return self.checkrealm()
                
            elif (command=='sendrealm'):
                realm_id=j[1].strip()
                usernameto = j[2].strip()
                message=""
                for w in j[3:]:
                   message="{} {}" . format(message,w)
                return self.sendrealm(realm_id,usernameto,message)

            elif (command=='inboxrealm'):
                realm_id=j[1].strip()
                return self.inboxrealm(realm_id)
            
            elif command == 'sendgrouprealm':
                realm_id = j[1].strip()
                groupname = j[2].strip()
                message=""
                for w in j[3:]:
                   message="{} {}" . format(message,w)
                return self.sendgrouprealm(realm_id, groupname, message)
            
            elif (command=='inboxgrouprealm'):
                realm_id=j[1].strip()
                groupname=j[2].strip()
                return self.inboxgrouprealm(realm_id,groupname)
            
            
            else:
                return "*Maaf, command tidak benar"
        except IndexError:
                return "-Maaf, command tidak benar"

    def sendstring(self,string):
        try:
            print("send data: {}" . format(string))
            self.sock.sendall(string.encode())
            receivemsg = ""
            while True:
                data = self.sock.recv(64)
                print("diterima dari server",data)
                if (data):
                    receivemsg = "{}{}" . format(receivemsg,data.decode())  #data harus didecode agar dapat di operasikan dalam bentuk string
                    if receivemsg[-4:]=='\r\n\r\n':
                        print("end of string")
                        return json.loads(receivemsg)
        except:
            self.sock.close()
            return { 'status' : 'ERROR', 'message' : 'Gagal'}
        
    def receive_messages(self):
        try:
            while True:
                data = self.sock2.recv(64)
                print("COKKKKKKKKKK",data)
                if (data):
                    receivemsg = "{}{}" . format(receivemsg,data.decode())  #data harus didecode agar dapat di operasikan dalam bentuk string
                    if receivemsg[-4:]=='\r\n\r\n':
                        print("end of string")
                        return json.loads(receivemsg)
        except:
            self.sock2.close()
            return { 'status' : 'ERROR', 'message' : 'Gagal'}
          

    def login(self,username,password):
        string="auth {} {} \r\n" . format(username,password)
        result = self.sendstring(string)
        if result['status']=='OK':
            self.tokenid=result['tokenid']
            self.username = username
            return "username {} logged in, token {} " .format(username,self.tokenid)
        else:
            return "Error, {}" . format(result['message'])
        
    def get_users(self):
        string = "users {} \r\n"
        result = self.sendstring(string)
        if result["status"] == "OK":
            return result["message"]
        else:
            return "Error, {}".format(result["message"])
    # Fitur autentikasi tambahan
    def register(self, username, email, password):
        print("PLISS MASUKKKK")
        string = "register {} {} {}\r\n".format(username, email, password)
        print("THIS IS STRINGGG", string)
        result = self.sendstring(string)
        if result["status"] == "OK":
            self.tokenid = result["tokenid"]
            return "username {} register in, token {} ".format(username, self.tokenid)
        else:
            return "Error, {}".format(result["message"])
        
    def logout(self):
        string = "logout \r\n"
        result = self.sendstring(string)
        if result["status"] == "OK":
            self.tokenid = ""
            return "user logged out"
        else:
            return "Error, {}".format(result["message"])

    def sendmessage(self,usernameto="xxx",message="xxx"):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="send {} {} {} \r\n" . format(self.tokenid,usernameto,message)
        print(string)
        result = self.sendstring(string)
        if result['status']=='OK':
            return {"status": "UPDATE", "receiver": usernameto, "sender": self.username, "messages": message}
        else:
            return "Error, {}" . format(result['message'])

    def inbox(self, username_from):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="inbox {} {}\r\n" . format(self.tokenid, username_from)
        result = self.sendstring(string)
        if result['status']=='OK':
            # return "{}" . format(json.dumps(result['messages']))
            return {"status": "OK", "messages": result['messages']}
        else:
            return "Error, {}" . format(result['message'])
    
    # Local Group-related
    def getgroups(self):
        string = "getgroups {} \r\n"
        result = self.sendstring(string)
        if result["status"] == "OK":
            return result["message"]
    
    def addgroup(self, groupname, password):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="addgroup {} {} {} \r\n" . format(self.tokenid, groupname, password)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "added {} group" . format(groupname)
        else:
            return "Error, {}" . format(result['message'])
        
    def joingroup(self, groupname, password):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="joingroup {} {} {} \r\n" . format(self.tokenid, groupname, password)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "joined {} group" . format(groupname)
        else:
            return "Error, {}" . format(result['message'])
    
    def sendgroup(self, groupname, message):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="sendgroup {} {} {} \r\n" . format(self.tokenid, groupname, message)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "group message sent to {} group" . format(groupname)
        else:
            return "Error, {}" . format(result['message'])
        
    def inboxgroup(self, groupname):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="inboxgroup {} {}\r\n" . format(self.tokenid, groupname)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "{}" . format(json.dumps(result['messages']))
        else:
            return "Error, {}" . format(result['message'])

    def addrealm(self, realm_id, realm_address, realm_port):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="addrealm {} {} {}\r\n" . format(realm_id, realm_address, realm_port, self.address_ip, self.address_port)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "added {} realm" . format(realm_id)
        else:
            return "Error, {}" . format(result['message'])
        
    def checkrealm(self):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="checkrealm\r\n"
        result = self.sendstring(string)
        if result['status']=='OK':
            return "returned realm list: {}".format(json.dumps(result['message']))
        else:
            return "Error, {}" . format(result['message'])
    
    def sendrealm(self, realm_id, usernameto, message):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="sendrealm {} {} {} {} {} {}\r\n" . format(self.address_ip, self.address_port, self.tokenid, realm_id, usernameto, message)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "realm message sent to user {} realm {}" . format(usernameto, realm_id)
        else:
            return "Error, {}" . format(result['message'])
        
    def inboxrealm(self, realm_id):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="inboxrealm {} {}\r\n" . format(self.tokenid, realm_id)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "{}" . format(json.dumps(result['messages']))
        else:
            return "Error, {}" . format(result['message'])
        
    def sendgrouprealm(self, realm_id, groupname, message):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="sendgrouprealm {} {} {} {} {} {} \r\n" . format(self.address_ip, self.address_port, self.tokenid, realm_id, groupname, message)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "group message sent to {} group in realm {}" . format(groupname, realm_id)
        else:
            return "Error, {}" . format(result['message'])

    def inboxgrouprealm(self, realm_id, groupname):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="inboxgrouprealm {} {} {}\r\n" . format(self.tokenid, realm_id, groupname)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "{}" . format(json.dumps(result['messages']))
        else:
            return "Error, {}" . format(result['message'])
  


if __name__=="__main__":
    cc = ChatClient()
    while True:
        cmdline = input("Command {}:" . format(cc.tokenid))
        print(cc.proses(cmdline))

