CREATE DATABASE IF NOT EXISTS chatapp2;

USE chatapp2;

-- Drop tables if they exist
DROP TABLE IF EXISTS group_chats;
DROP TABLE IF EXISTS chats;
DROP TABLE IF EXISTS group_members;
DROP TABLE IF EXISTS chat_groups;
DROP TABLE IF EXISTS users;

-- Create tables
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_groups (
    group_id INT PRIMARY KEY AUTO_INCREMENT,
    group_name VARCHAR(100) NOT NULL,
    password VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE group_members (
    group_member_id INT PRIMARY KEY AUTO_INCREMENT,
    group_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES chat_groups(group_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE chats (
    chat_id INT PRIMARY KEY AUTO_INCREMENT,
    message TEXT NOT NULL,
    sender_id INT NOT NULL,
    receiver_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (receiver_id) REFERENCES users(user_id)
);

CREATE TABLE group_chats (
    group_chat_id INT PRIMARY KEY AUTO_INCREMENT,
    group_id INT NOT NULL,
    sender_id INT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES chat_groups(group_id),
    FOREIGN KEY (sender_id) REFERENCES users(user_id)
);
