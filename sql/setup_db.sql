-- HomeFinder Portal — Database Setup
-- Run once: mysql -u root -p < setup_db.sql

CREATE DATABASE IF NOT EXISTS user_auth
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE user_auth;

SOURCE schema.sql;
