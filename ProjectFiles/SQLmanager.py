import datetime
import os
import re
import sqlite3
import websockets
import websocket
import asyncio
import json
import requests
import asyncio
import threading
import queue
import time
import chromadb
import gradio as gr
import streamlit as st
import PySimpleGUI as sg
import conteneiro
import pdfplumber
import websocket_manager
from io import BytesIO
from agent_neural import NeuralAgent
from agents_neural import Fireworks, Copilot, ChatGPT, Claude3, ForefrontAI, Flowise, Chaindesk, CharacterAI
from langchain.tools import BaseTool, StructuredTool, tool
from langchain.vectorstores import Chroma
from langchain.document_loaders import PyPDFLoader, TextLoader

class SQLmanagement:

    def __init__(self):
        self.conn = sqlite3.connect('Project_management.db')
        self.cursor = self.conn.cursor()

        # Create tables
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Projects (
            name TEXT PRIMARY KEY,
            description TEXT,
            plan TEXT,
            agents TEXT,
            files TEXT,
            status TEXT
        )''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Agents (
            name TEXT PRIMARY KEY,
            role TEXT,
            projects TEXT
        )''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT,
            project_name TEXT,
            task_description TEXT,
            status TEXT,
            FOREIGN KEY (project_name) REFERENCES Projects (project_name)
        )''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Files (
            name TEXT PRIMARY KEY,
            path TEXT,
            description TEXT,
            projects TEXT
        )''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_agents (
                project_name TEXT,
                agent_name TEXT,
                FOREIGN KEY (project_name) REFERENCES Projects(name),
                FOREIGN KEY (agent_name) REFERENCES Agents(name),
                PRIMARY KEY (project_name, agent_name)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_files (
                project_name TEXT,
                file_name TEXT,
                FOREIGN KEY (project_name) REFERENCES Projects(name),
                FOREIGN KEY (file_name) REFERENCES Files(name),
                PRIMARY KEY (project_name, file_name)
            )
        ''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS ProjectHistory (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT,
            description TEXT,
            plan TEXT,
            status TEXT,
            agents TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS AgentHistory (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            name TEXT,
            role TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS TaskHistory (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            project_id INTEGER,
            description TEXT,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS FileHistory (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            name TEXT,
            path TEXT,
            description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')           

        self.conn.commit()
        self.conn.close()    

    def add_project(self, name, description, plan, status):
        self.conn = sqlite3.connect('Project_management.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''INSERT INTO Projects (name, description, plan, status)
                        VALUES (?, ?, ?, ?)''', (name, description, plan, status))
        self.conn.commit()
        self.conn.close()

    def get_projects(self):
        conn = sqlite3.connect('Project_management.db')
        self.cursor = conn.cursor()
        self.cursor.execute('''SELECT name, description, agents, files, status FROM Projects''')
        projects = self.cursor.fetchall()
        conn.close()
        return projects
    
    def add_agent(self, name, role):
        self.conn = sqlite3.connect('Project_management.db')
        cursor = self.conn.cursor()
        cursor.execute('''INSERT INTO Agents (name, role)
                        VALUES (?, ?)''', (name, role))
        self.conn.commit()
        self.conn.close()

    def get_agents(self):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT name, projects FROM Agents''')
        agents = cursor.fetchall()
        conn.close()
        return agents    
        
    def add_file(self, name, path, description):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO Files (name, path, description)
                        VALUES (?, ?, ?)''', (name, path, description))
        conn.commit()
        conn.close()

    def get_files(self):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM Files''')
        files = cursor.fetchall()
        conn.close()
        return files    

    def get_project_by_name(self, project_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM Projects WHERE name = ?''', (project_name,))
        project = cursor.fetchone()
        conn.close()
        return project   

    def get_agent_by_name(self, agent_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM Agents WHERE name = ?''', (agent_name,))
        agent = cursor.fetchone()
        conn.close()
        return agent   

    def get_file_by_name(self, file_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM Files WHERE name = ?''', (file_name,))
        file = cursor.fetchone()
        conn.close()
        return file   

    def update_project(self, name, description, plan, agents, files, status):
        conn = sqlite3.connect('Project_management.db')
        self.cursor = conn.cursor()
        self.cursor.execute('''UPDATE Projects
                        SET name = ?, description = ?, plan = ?, agents = ?, files = ?, status = ?
                        WHERE name = ?''', (name, description, plan, agents, files, status))
        conn.commit()
        conn.close()

    def add_agent_to_project(self, project_name, agent_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO project_agents (project_name, agent_name)
                        VALUES (?, ?)''', (project_name, agent_name))
        conn.commit()
        conn.close()

    def remove_agent_from_project(self, project_name, agent_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''DELETE FROM ProjectAgents WHERE project_name = ? AND agent_name = ?''', (project_name, agent_name))
        conn.commit()
        conn.close()

    def get_project_agents(self, project_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT Agents.name
                        FROM Agents
                        JOIN project_agents ON Agents.name = project_agents.agent_name
                        WHERE project_agents.project_name = ?''', (project_name,))
        agents = cursor.fetchall()
        conn.close()
        return agents
    
    def get_project_files(self, project_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT Files.name, Files.path
                        FROM Files
                        JOIN project_files ON Files.name = project_files.file_name
                        WHERE project_files.project_name = ?''', (project_name,))
        files = cursor.fetchall()
        conn.close()
        return files

    def get_agent_projects(self, agent_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT Projects.name, Projects.description, Projects.status
                        FROM Projects
                        JOIN project_agents ON Projects.name = project_agents.project_name
                        WHERE project_agents.agent_name = ?''', (agent_name,))
        projects = cursor.fetchall()
        conn.close()
        return projects

    def get_file_projects(self, file_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT Projects.name, Projects.description, Projects.status
                        FROM Projects
                        JOIN project_files ON Projects.name = project_files.project_name
                        WHERE project_files.file_name = ?''', (file_name,))
        projects = cursor.fetchall()
        conn.close()
        return projects

    def get_agents_for_project(self, project_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT Agents.name
                        FROM Agents
                        JOIN project_agents ON Agents.name = project_agents.name
                        WHERE project_agents.project_name = ?''', (project_name,))
        agents = cursor.fetchall()
        conn.close()
        return agents

    def get_projects_for_agent(self, agent_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT Projects.name, Projects.description
                          FROM Projects
                          JOIN project_agents ON Projects.name = project_agents.project_name
                          WHERE project_agents.agent_name = ?''', (agent_name,))
        projects = cursor.fetchall()
        conn.close()
        return projects
    
    def update_agent_name(self, old_name, new_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Agents SET name = ? WHERE name = ?''', (new_name, old_name))
        cursor.execute('''UPDATE project_agents SET agent_name = ? WHERE agent_name = ?''', (new_name, old_name))
        conn.commit()
        conn.close()

    def update_agent_role(self, agent_name, role):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Agents SET role = ? WHERE name = ?''', (role, agent_name))
        conn.commit()
        conn.close()

    def update_agent_projects(self, agent_name, projects):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Agents SET projects = ? WHERE name = ?''', (projects, agent_name))
        conn.commit()
        conn.close()

    def update_project_name(self, project_name, new_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Projects SET name = ? WHERE name = ?''', (new_name, project_name))
        conn.commit()
        conn.close()

    def update_project_description(self, project_name, new_description):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Projects SET description = ? WHERE name = ?''', (new_description, project_name))
        conn.commit()
        conn.close()

    def update_project_plan(self, project_name, new_plan):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Projects SET plan = ? WHERE name = ?''', (new_plan, project_name))
        conn.commit()
        conn.close()

    def update_project_status(self, project_name, new_status):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Projects SET status = ? WHERE name = ?''', (new_status, project_name))
        conn.commit()
        conn.close()    

    def update_project_agents(self, project_name, agents):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Projects SET agents = ? WHERE name = ?''', (agents, project_name))
        conn.commit()
        conn.close() 

    def update_project_files(self, project_name, files):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Projects SET files = ? WHERE name = ?''', (files, project_name))
        conn.commit()
        conn.close() 

    def update_file_projects(self, file_name, projects):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Files SET projects = ? WHERE name = ?''', (projects, file_name))
        conn.commit()
        conn.close() 

    def add_file_to_project(self, project_name, file_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO project_files (project_name, file_name)
                        VALUES (?, ?)''', (project_name, file_name))
        conn.commit()
        conn.close()

    def remove_file_from_project(self, project_name, file):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''DELETE FROM project_files WHERE project_name = ? AND file_name = ?''', (project_name, file))
        conn.commit()
        conn.close()

    def get_files_for_project(self, project_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT Files.name, Files.path, Files.description
                        FROM Files
                        JOIN project_files ON Files.name = project_files.file_name
                        WHERE project_files.project_name = ?''', (project_name,))
        files = cursor.fetchall()
        conn.close()
        return files

    def update_file_name(self, file_name, new_name):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Files SET name = ? WHERE name = ?''', (new_name, file_name))
        conn.commit()
        conn.close()

    def update_file_path(self, file_name, new_path):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Files SET path = ? WHERE name = ?''', (new_path, file_name))
        conn.commit()
        conn.close()

    def update_file_description(self, file_name, new_description):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Files SET description = ? WHERE name = ?''', (new_description, file_name))
        conn.commit()
        conn.close()

    def update_file(self, file_name, new_name, new_path, new_description, association):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Files
                        SET name = ?, path = ?, description = ?
                        WHERE name = ?''', (new_name, new_path, new_description, file_name))
        conn.commit()
        conn.close()

    def update_agent(self, agent_name, new_name, new_role, new_assignment):
        conn = sqlite3.connect('Project_management.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE Agents
                        SET ame = ?, role = ?
                        WHERE name = ?''', (new_name, new_role, agent_name))
        conn.commit()
        conn.close()

    def delete_file(self, file_name):
        conn = sqlite3.connect('Project_management.db')
        self.cursor = conn.cursor()
        self.cursor.execute('''DELETE FROM Files WHERE name = ?''', (file_name,))
        conn.commit()
        conn.close()

    def delete_agent(self, agent_name):
        conn = sqlite3.connect('Project_management.db')
        self.cursor = conn.cursor()
        self.cursor.execute('''DELETE FROM Agents WHERE name = ?''', (agent_name,))
        conn.commit()
        conn.close()

    def delete_project(self, project_name):
        conn = sqlite3.connect('Project_management.db')
        self.cursor = conn.cursor()
        self.cursor.execute('''DELETE FROM Projects WHERE name = ?''', (project_name,))
        conn.commit()
        conn.close()

    async def removeFile(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement  
        files = self.get_files()
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for removing data regarding a chosen file from a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide the name of file which should be removed according to information received in the input message."""            
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to remove a file data from the database in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to choose the file which has to be removed from the following list of files and give it's name in your response.
        ---- 
        {files}
        ----
        Please respond with the name of file that has to be removed and nothing else."""   
        
        history.append(msgCli) 
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
        data = json.loads(resp)
        file_name = data['message']
        history.append(file_name) 
        inputs.append(msgCli)
        outputs.append(file_name)
        window.write_event_value('-WRITE_COMMAND-', (file_name, follow_up))
        self.delete_file(file_name)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"File: {file_name} has been successfuly removed from database. (time: {timestamp})"
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return mes

    async def removeAgent(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement  
        agents = self.get_agents()
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for removing data regarding chosen agents from a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide the name of agent which should be removed according to information received in the input message."""            
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to remove a agent data from the database in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to choose the agent which has to be removed from the following list of files and give it's name in your response.
        ---- 
        {agents}
        ----
        Please respond with the name of agent that has to be removed and nothing else."""   
        
        history.append(msgCli) 
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
        data = json.loads(resp)
        agent_name = data['message']
        history.append(agent_name) 
        inputs.append(msgCli)
        outputs.append(agent_name)
        window.write_event_value('-WRITE_COMMAND-', (agent_name, follow_up))
        self.delete_agent(agent_name)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Agent: {agent_name} has been successfuly removed from database. (time: {timestamp})"
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return mes

    async def removeProject(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement  
        projects = self.get_projects()
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for removing data regarding chosen project(s) from a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide the name of the project which should be removed according to information received in the input message."""            
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to remove a project data from the database in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to choose the project which has to be removed from the following list of files and give it's name in your response.
        ---- 
        {projects}
        ----
        Please respond with the name of project that has to be removed and nothing else."""   
        
        history.append(msgCli) 
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
        data = json.loads(resp)
        project_name = data['message']
        history.append(project_name) 
        inputs.append(msgCli)
        outputs.append(project_name)
        window.write_event_value('-WRITE_COMMAND-', (project_name, follow_up))
        self.delete_project(project_name)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Project: {project_name} has been successfuly removed from database. (time: {timestamp})"
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return mes

    async def updateFileName(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, file_name):
        if gui == 'PySimpleGUI':
            window = UIelement  
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a previousy selected file which is stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide an updated (new) name of selected file which is consistent with information received in the input message."""            
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update name of the agent file you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to provide an updated (new) name of selected file consistent with information received in the message above. This is the current name of selected file: {file_name}. Please respond with the updated name and nothing else."""   
        
        history.append(msgCli) 
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
        data = json.loads(resp)
        new_name = data['message']
        history.append(new_name) 
        inputs.append(msgCli)
        outputs.append(new_name)
        window.write_event_value('-WRITE_COMMAND-', (new_name, follow_up))
        self.update_file_name(file_name, new_name)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Name of the selected file has been updated from: {file_name} to the following one: {new_name}. (time: {timestamp})"
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return mes

    async def updateFilePath(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, file_name):
        if gui == 'PySimpleGUI':
            window = UIelement
        file = self.get_file_by_name(file_name)  
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a previously selected file which is stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide an updated (new) path to selected file which is consistent with information received in the input message."""            
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update path to file you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to provide an updated (new) path to previously selected file: {file_name} consistent with information received in the message above. 
        This is the current path to selected file: {file[2]}. Please respond with the updated path and nothing else."""   
        
        history.append(msgCli) 
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
        data = json.loads(resp)
        new_path = data['message']
        history.append(new_path) 
        inputs.append(msgCli)
        outputs.append(new_path)
        window.write_event_value('-WRITE_COMMAND-', (new_path, follow_up))
        self.update_file_path(file_name, new_path)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Path to the selected file has been updated from: {file[2]} to the following one: {new_path}. (time: {timestamp})"
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return mes

    async def updateFileDescription(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, file_name):
        if gui == 'PySimpleGUI':
            window = UIelement
        file = self.get_file_by_name(file_name)  
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a previously selected file which is stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide an updated (new) description of selected file which is consistent with information received in the input message."""            
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update description of file you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to provide an updated (new) description of previously selected file: {file_name} consistent with information received in the message above. 
        This is the current description of selected file: {file[3]}. Please respond with the updated description and nothing else."""   
        
        history.append(msgCli) 
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 700)
        data = json.loads(resp)
        new_description = data['message']
        history.append(new_description) 
        inputs.append(msgCli)
        outputs.append(new_description)
        window.write_event_value('-WRITE_COMMAND-', (new_description, follow_up))
        self.update_file_description(file_name, new_description)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Description of the selected file: {file_name} has been updated from: {file[3]} to the following one: {new_description}. (time: {timestamp})"
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return mes

    async def addFileToProject(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, name, source):
        if gui == 'PySimpleGUI':
            window = UIelement  
        files = self.get_files()
        projects = self.get_projects()

        if source == 'project':
            project_name = name
            sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for associating files with projects in the data stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.
            Your main and only job is to provide the name of file which has to be added to previously selected project accordingly to information received in the input message."""            
            
            msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to add a local file to a project which you've previously selected in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to provide name of the file which has to be added to project: {project_name}:
            ----
            {files}                    
            ----
            Please, answer only with the name of file (including extension/format - like: 'example.txt') which you want to add to selected project and nothing else as your entire response will be recorded in the database in it's exact form."""
            history.append(msgCli)
            resp = await neural.askAgent(sys_msg, msgCli, 50)
            data = json.loads(resp)
            file_name = data['message'] 
            history.append(file_name) 
            inputs.append(msgCli)
            outputs.append(file_name)               
            window.write_event_value('-WRITE_COMMAND-', (file_name, follow_up))


        if source == 'file':
            file_name = name
            sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for associating files with projects in the data stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.
            Your main and only job is to provide the name of project to which previously selected file has to be added to accordingly to information received in the input message."""            
            
            msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to add a previously selected file: {file_name} to a project specified in following input message:
            ----
            {msg}
            ----
            Your main and only job is to provide name of the project to which file: {file_name} has to be added. Below is the list of currently ongoing projects:
            ----
            {projects}                    
            ----
            Please, answer only with the name of project which to you want to add the selected filw and nothing else as your entire response will be used in it's exact form to retrieve data from database."""
            
            history.append(msgCli)
            resp = await neural.askAgent(sys_msg, msgCli, 20)
            data = json.loads(resp)
            project_name = data['message']
            history.append(project_name)
            inputs.append(msgCli)
            outputs.append(project_name)   
            window.write_event_value('-WRITE_COMMAND-', (project_name, follow_up))


        self.add_file_to_project(project_name, file_name)
        files2 = self.get_files_for_project(project_name)          
        projects2 = self.get_projects_for_file(file_name)
        self.update_file_projects(file_name, projects2)
        self.update_project_files(project_name, files2)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"File {file_name} has been succe4ssfully added to project: {project_name} (time: {timestamp})"
        history.append(mes)
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))


    async def removeFileFromProject(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, name, source):
        if gui == 'PySimpleGUI':
            window = UIelement

        if source == 'file':
            file_name = name    
            file = self.get_file_by_name(file_name) 
            sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for removing agents from currently ongoing projects if their work is done or they were added to project improperly.
            Your main and only job is to provide the name of project from which selected file has to be removed according to information provided in the input message."""            
            
            msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to remove a file from project(s) in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to provide name of the project from which selected agent has to be removed.
            List of all projects with which file: {file_name} was previously associated, is available here:
            ----
            {file[4]}                    
            ----
            Please, answer only with the name of project from the list above, to remove file: {file_name} from it."""
            
            history.append(msgCli) 
            resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
            data = json.loads(resp)
            project_name = data['message']       
            window.write_event_value('-WRITE_COMMAND-', (project_name, follow_up)) 

        if source == 'project':
            project_name = name    
            project = self.get_project_by_name(project_name) 
            sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for removing files from currently ongoing projects if their work is done or they were added to project improperly.
            Your main and only job is to provide the name of file which has to be removed from previously selected project according to information provided in the input message."""            
            
            msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to remove an agent from project(s) in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to provide name of the file which has to be removed from previously selected project.
            List of all files associated with the project: {project_name}, is available here:
            ----
            {project[5]}                    
            ----
            Please, answer only with the name of file from the list above ijn order to remove it from project {project_name}z."""            
            history.append(msgCli) 
            resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
            data = json.loads(resp)
            project_name = data['message']       
            window.write_event_value('-WRITE_COMMAND-', (project_name, follow_up)) 

        self.remove_file_from_project(project_name, file_name)
        files2 = self.get_files_for_project(project_name)          
        projects2 = self.get_projects_for_file(file_name)
        self.update_file_projects(file_name, projects2)
        self.update_project_files(project_name, files2)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"File {file_name} has been succe4ssfully removed from the project: {project_name}. (time: {timestamp})"
        print(mes)
        history.append(mes) 
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return mes     

    async def assignAgentToProject(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, name, source):
        if gui == 'PySimpleGUI':
            window = UIelement
        projects = self.get_projects()
        agents = self.get_agents()

        if source == 'agent':
            agent_name = name
            sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for adding new agents to projects selected from a list of all ongoing projects which is stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.
            Your main and only job is to provide the name of project to which you want to add the selected agent, accordingly to information received in the input message."""            
            
            msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to add selected agent to a project of tour choice in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to provide name of the project to which the previously selected agent: {agent_name} has to be added. Here is the curent list of all ongoing projects:
            ----
            {projects}                    
            ----
            Please, answer only with the name of agent you want to add to selected project and anything else as your entire response will be used in it's exact form to retrieve data from a localo database."""
            
            history.append(msgCli)
            resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
            data = json.loads(resp)
            project_name = data['message']      
            history.append(project_name) 
            inputs.append(msgCli)
            outputs.append(project_name)
            window.write_event_value('-WRITE_COMMAND-', (project_name, follow_up))  

        if source == 'project':
            project_name = name
            sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for associating agents with projects in the data stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.
            Your main and only job is to provide the name of agent which has to be added to previously selected project accordingly to information received in the input message."""            
            
            msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to associat an agent with a project which you've previously selected in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to provide name of the agent which has to be added to project: {project_name}:
            ----
            {agents}                    
            ----
            Please, answer only with the name of file (including extension/format - like: 'example.txt') which you want to add to selected project and nothing else as your entire response will be recorded in the database in it's exact form."""
            history.append(msgCli)
            resp = await neural.askAgent(sys_msg, msgCli, 50)
            data = json.loads(resp)
            file_name = data['message'] 
            history.append(file_name) 
            inputs.append(msgCli)
            outputs.append(file_name)               
            window.write_event_value('-WRITE_COMMAND-', (file_name, follow_up))  

        self.add_agent_to_project(project_name, agent_name)
        agents2 = self.get_agents_for_project(project_name)
        projects2 = self.get_projects_for_agent(agent_name)
        self.update_agent_projects(agent_name, projects2)
        self.update_project_agents(project_name, agents2)
        mes = f"Agent {agent_name} has been successfully added to the project: {project_name}."

        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return mes

    async def removeAgentFromProject(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, name, source):
        if gui == 'PySimpleGUI':
            window = UIelement

        if source == 'agent':
            agent_name = name    
            agent = self.get_agent_by_name(agent_name) 
            sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for removing agents from currently ongoing projects if their work is done or they were added to project improperly.
            Your main and only job is to provide the name of project from which selected agent has to be removed according to information provided in the input message."""            
            
            msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to remove an agent from project(s) in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to provide name of the project from which selected agent has to be removed.
            List of all projects to which agent: {agent_name} was previously added, is available here:
            ----
            {agent[3]}                    
            ----
            Please, answer only with the name of project from the list above, to remove {agent_name} from it."""
            
            history.append(msgCli) 
            resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
            data = json.loads(resp)
            project_name = data['message']       
            window.write_event_value('-WRITE_COMMAND-', (project_name, follow_up)) 

        if source == 'project':
            project_name = name    
            project = self.get_project_by_name(project_name) 
            sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for removing agents from currently ongoing projects if their work is done or they were added to project improperly.
            Your main and only job is to provide the name of agent which has to be removed from previously selected project according to information provided in the input message."""            
            
            msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to remove an agent from project(s) in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to provide name of the agent which has to be removed from previously selected project.
            List of all agents associated with the project: {project_name}, is available here:
            ----
            {project[4]}                    
            ----
            Please, answer only with the name of agent from the list above ijn order to remove it from project {project_name}z."""            
            history.append(msgCli) 
            resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
            data = json.loads(resp)
            project_name = data['message']       
            window.write_event_value('-WRITE_COMMAND-', (project_name, follow_up)) 

        self.remove_agent_from_project(project_name, agent_name)
        agents2 = self.get_agents_for_project(project_name)
        projects2 = self.get_projects_for_agent(agent_name)
        self.update_agent_projects(agent_name, projects2)
        self.update_project_agents(project_name, agents2)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Agent {agent_name} has been succe4ssfully removed from the project: {project_name}. (time: {timestamp})"
        print(mes)
        history.append(mes) 
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return mes     

    async def updateAgentName(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, agent_name):
        if gui == 'PySimpleGUI':
            window = UIelement  
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected agent which is stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide an updated (new) name of selected agent which is consistent with information received in the input message."""            
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update name of the agent which you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to provide an updated (new) name of selected agent consistent with information received in the message above. This is the name of currently selected agent: {agent_name}. Please respond with the updated name and nothing else."""   
        
        history.append(msgCli) 
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
        data = json.loads(resp)
        new_name = data['message']
        history.append(new_name) 
        inputs.append(msgCli)
        outputs.append(new_name)
        window.write_event_value('-WRITE_COMMAND-', (new_name, follow_up))
        self.update_agent_name(agent_name, new_name)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Name of the selected agent has been updated from: {agent_name} to the following one: {new_name}. (time: {timestamp})"
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        return new_name
    
    async def updateAgentRole(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, agent_name):
        if gui == 'PySimpleGUI':
            window = UIelement  
        agent = self.get_agent_by_name(agent_name)
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected agent which is stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide an updated (new) role/function of selected agent which is consistent with information received in the input message."""            
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update the role/function of an agent which you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to provide an updated (new) role/function of selected agent consistent with information received in the message above. This is the current role/function of selected agent:
        ----
        {agent[2]}
        ----
        Please respond with the updated role/function and nothing else as your response will be saved in the database as agent's function in it's exact form."""   
        
        history.append(msgCli) 
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 15)
        data = json.loads(resp)
        new_role = data['message']
        history.append(new_role) 
        inputs.append(msgCli)
        outputs.append(new_role)
        window.write_event_value('-WRITE_COMMAND-', (new_role, follow_up))
        self.update_agent_name(agent_name, new_role)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Role of the selected project has been updated to the following one: {new_role}. (time: {timestamp})"
        return mes

    async def editProjectName(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, project_name):
        if gui == 'PySimpleGUI':
            window = UIelement  
        sys_msg2 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected project stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide an updated (new) name of selected project consistent with information received in the input message."""            
        msgCli2 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update the name of an ongoing project which you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to provide an updated (new) name of selected project consistent with information received in the message above. The current name of selected project is: {project_name}. Please respond with the updated name and nothing else."""   
        history.append(msgCli2) 
        resp = await neural.askAgent(sys_msg2, inputs, outputs, msgCli2, 10)
        data = json.loads(resp)
        new_name = data['message']
        history.append(new_name) 
        inputs.append(msgCli2)
        outputs.append(new_name)
        window.write_event_value('-WRITE_COMMAND-', (new_name, follow_up))
        self.update_project_name(project_name, new_name)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Name of the selected project has been updated to the following one: {new_name}. (time: {timestamp})"
        return mes

    async def editProjectDescription(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, project_name):
        if gui == 'PySimpleGUI':
            window = UIelement  
        project = self.get_project_by_name(project_name)   
        sys_msg2 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected project stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide an updated (new) description of selected project consistent with information received in the input message."""            
        msgCli2 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update the description of ongoing project which you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to provide an updated (new) description of selected project consistent with information received in the message above. The current description of selected project is: {project[2]}. Please respond with the updated name and nothing else."""   
        history.append(msgCli2) 
        resp = await neural.askAgent(sys_msg2, inputs, outputs, msgCli2, 500)
        data = json.loads(resp)
        description = data['message']                
        history.append(description) 
        inputs.append(msgCli2)
        outputs.append(description)
        window.write_event_value('-WRITE_COMMAND-', (description, follow_up))
        self.update_project_name(project_name, description)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Description of the selected project has been updated to the following one: {description} (time: {timestamp})"
        return mes
    
    async def editProjectPlan(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, project_name):
        if gui == 'PySimpleGUI':
            window = UIelement  
        project = self.get_project_by_name(project_name)      
        sys_msg2 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected project stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide an updated (new) plan of selected project consistent with information received in the input message."""            
        msgCli2 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update the current plan of ongoing project which you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to provide an updated (new) plan of selected project consistent with information received in the message above. The current plan of selected project is: 
        ----
        {project[3]}
        ----
        Please respond with the updated name and nothing else."""
        
        history.append(msgCli2)
        resp = await neural.askAgent(sys_msg2, msgCli2, 3500)
        data = json.loads(resp)
        plan = data['message']
        history.append(plan) 
        inputs.append(msgCli2)
        outputs.append(plan)
        window.write_event_value('-WRITE_COMMAND-', (plan, follow_up))
        self.update_project_plan(project_name, plan)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Plan of selected project has been updated to the following one: {plan}. (time: {timestamp})"
        return mes

    async def editProjectStatus(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up, project_name):
        if gui == 'PySimpleGUI':
            window = UIelement
        project = self.get_project_by_name(project_name)    
        sys_msg2 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected project stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to provide an updated (new) status (work progress) of the selected project consistent with information received in the input message."""            
        msgCli2 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update the current status of ongoing project which you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to provide an updated (new) status of selected project and make it consistent with information received in the message above. The current status of selected project is: {project[5]}. Please respond with the updated name and nothing else."""
        history.append(msgCli2)
        resp = await neural.askAgent(sys_msg2, msgCli2, 500)
        data = json.loads(resp)
        status = data['message']
        history.append(status) 
        inputs.append(msgCli2)
        outputs.append(status)
        window.write_event_value('-WRITE_COMMAND-', (status, follow_up))
        self.update_project_status(project_name, status)
        timestamp = datetime.datetime.now().isoformat()
        mes = f"Status of selected project has been changed to: {status}. (time: {timestamp})"
        return mes
    
    async def SQLdecide(self, UIelement, gui, follow_up, neural, history, inputs, outputs, msg, instruction):
        if gui == 'PySimpleGUI':
            window = UIelement   
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for performing operations on a local SQL database containing data about varius ongoing large-scale projects but also for retrieving data from that database to keep other cooperating agents updated on current projects and updating the data accordingly to informaqtion received from other fellow agents. Because your responses are selected to be used as the main response logic of an autonomous node in the NeuralGPT framework, besides exectuing operations on the local SQL database, you are also capable to give 'normal' full-lenght answers to inputs, if you consider it to be the right way for you to respond. Your main and only role is to decide if in response to incoming message you should perform an operation on local SQL database or to give a full-lenght answer and respond with one of the following commands associated with your decision:
        - '/giveAnswer' to respond with a full-lenght answer to given input
        - '/takeAction' to perform an operation on local project database in response to givn input
        Remember that It is crucial for you to respond only with one of those commands in their exact forms and nothing else."""
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically because your responses are selected to be used as the main response logic of an autonomous node in the NeuralGPT framework and you have just received a message from another fellow agent in the NeuralGPT framework:
        ----
        {msg}
        ----
        Besides exectuing operations on the local SQL database, you are also capable to give 'normal' full-lenght answers to inputs, if you consider it to be the right way for you to respond. Your main and only role is to decide if in response to incoming message you should perform an operation on local SQL database or to give a full-lenght answer and respond with one of the following commands associated with your decision:
        - '/giveAnswer' to respond with a full-lenght answer to given input
        - '/takeAction' to perform an operation on local project database in response to givn input
        Remember that It is crucial for you to respond only with one of those commands in their exact forms and nothing else."""

        history.append(msgCli) 
        try:
            response = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 5)
            print(response)
            data = json.loads(response)
            resp = data['message']
            name = data['name']
            answer = f"{name}: {resp}"
            
            history.append(resp) 
            inputs.append(msgCli)
            outputs.append(resp)
            
            window.write_event_value('-WRITE_COMMAND-', (answer, follow_up))

            if re.search(r'/giveAnswer', str(resp)):
                if follow_up == 'client':
                    response1 = await neural.ask2(instruction, msg, 2500)
                else:
                    response1 = await neural.ask(instruction, msg, 3500)
                print(response1)
                
            if re.search(r'/takeAction', str(resp)):
                response1 = await self.SQLagent(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
                print(response1)

            return response1

        except Exception as e:
            print(f"Error: {e}")     

    async def editFileList(self, UIelement, gui, follow_up, neural, history, inputs, outputs, msg):
        if gui == 'PySimpleGUI':
            window = UIelement   
        files = self.get_files()
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected project stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to deciede what action should be taken in response to incoming message and answer with one of following commands associated with your decision:
        - '/addNewFile' to add new file to the list. Use only (!!!) if that file wasn't already recorded in the database.
        - '/updateFileData' in order to update/change available information regarding a file of your choice.
        - anything else will stop the updating process
        Please, respond with one of those commands and nothing else."""   
        
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update formation about local files in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to decide what action you should take in response to the message above. The current list of all recorded files is available here:
        ----
        {files}
        ----
        Make sure if the file you might want to add to the database, isn't already recorded in it. If it is, DO NOT add the same agent for the second time but (if necessary) update data associated with that agent to make it fully consistent with the input message
        Please respond with one of the following commands associated with the action you wish to take:
        - '/addNewFile' to add new file to the list. Use only (!!!) if that file wasn't already recorded in the database.
        - '/updateFileData' in order to update/change available information regarding a file of your choice.
        - '/removeFileData'  to remove information about a chosen file from database
        - anything else will stop the updating process
        Please, respond with one of those commands and nothing else."""
        
        history.append(msgCli)
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 10)
        data = json.loads(resp)
        txt = data['message']
        name = data['name']
        edit = f"{name}: {txt}"
        history.append(edit) 
        inputs.append(msgCli)
        outputs.append(edit)
        window.write_event_value('-WRITE_COMMAND-', (edit, follow_up))

        if re.search(r'/addNewFile', str(txt)):
            mes = self.addFile(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            print(mes)
        
        if re.search(r'/updateFileData', str(edit)):    
            mes = self.updateFile(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            print(mes)

        if re.search(r'/removeFileData', str(edit)):    
            mes = self.removeFile(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            print(mes)

        else:
            mes = "Editing of files database was terminated."

        history.append(mes) 
        inputs.append(msgCli)
        outputs.append(mes)
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))
        
        sys_msg3 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating the list of files associated with the selected project which is stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.        Your main and only job is to provide the name of agent which has to be removed frokm the list of agents currently working on selected project which is consistent with information received in the input message.            
        Your main and only job, is to decide if you should continue editing the list of files or if no furter edits are needed for the list to be consistent with information in the input message and to answer with one of the following commands associated with your decision:
        - '/keepEditing' to continue changing the list of agents working currently on selected project
        - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
        Please, respond with one of those commands and nothing else."""

        msgCli3 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to update the list of agents working on the project which you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to decide if list of agents available below is consistent with the input message and you should finish editing it or if you need to continue editing the list: 
        {files}                    
        ----
        Please, respond with one of those commands and nothing else:
        - '/keepEditing' to continue changing the list of agents working currently on selected project
        - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
        """
        history.append(msgCli3) 
        resp = await neural.askAgent(sys_msg3, inputs, outputs, msgCli3, 15)
        data = json.loads(resp)
        decision = data['message']                    
        history.append(decision) 
        inputs.append(msgCli3)
        outputs.append(decision)
        window.write_event_value('-WRITE_COMMAND-', (decision, follow_up))

        if re.search(r'/keepEditing', str(decision)):
            await self.editFileList(UIelement, gui, follow_up, neural, history, inputs, outputs, msg)
        
        else:
            work = str(history)
            history.clear()
            inputs.clear()
            outputs.clear()
            
            return work

    async def editAgentList(self, UIelement, gui, follow_up, neural, history, inputs, outputs, msg):
        if gui == 'PySimpleGUI':
            window = UIelement   
        agents = self.get_agents()
        sys_msg2 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data stored in a local SQL database regarding agents cooperating within the NeuralGPT framework. It is an operation during which your responses will be used to retrieve specific data or recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        Your main and only job is to deciede what action should be taken in response to incoming message and answer with one of following commands associated with your decision:
        - '/addNewAgent' to add new agent to the list. Use only (!!!) if that agen't (or very similar one) wasn't already recorded in the database.
        - '/updateAgentData' in order to update/change available information regarding a selected agent.
        - '/removeAgentData' in order to delete data regarding a chosen agent from the database
        - anything else will stop the updating process
        Please, respond with one of those commands and nothing else."""   
        
        msgCli2 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to change/update list of agents working currently on project which you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to decide what action you should take in response to the message above. The current list of all agents is available here:
        ----
        {agents}
        ----
        Make sure if the agant you might want to add to the database, isn't already recorded in it. If it is, DO NOT add the same agent for the second time but (if necessary) update data associated with that agent to make it fully consistent with the input message
        Please respond with one of the following commands associated with the action you wish to take:
        - '/addNewAgent' to add new agent to the list. Use only (!!!) if that agen't (or very similar one) wasn't already recorded in the database.
        - '/updateAgentData' in order to update/change available information regarding a selected agent.
        - '/removeAgentData' in order to delete data regarding a chosen agent from the database
        - anything else will stop the updating process - remember to ALWAYS(!!!) do that if agent which you wanted to add is already assigned to selected project.
        Please, respond with one of those commands and nothing else."""
        history.append(msgCli2)
        agentList = await neural.askAgent(sys_msg2, inputs, outputs, msgCli2, 10)
        history.append(agentList) 
        inputs.append(msgCli2)
        outputs.append(agentList)
        window.write_event_value('-WRITE_COMMAND-', (agentList, follow_up))

        if re.search(r'/addNewAgent', str(agentList)):
            mes = await self.addAgent(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            print(mes)

        if re.search(r'/updateAgentData', str(agentList)):
            mes = await self.updateAgent(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            print(mes)

        if re.search(r'/removeAgentData', str(agentList)):
            mes = await self.removeAgent(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            print(mes)

        else:
            mes = "Editing of agent list was terminated due to invalid command."
            print(mes)

        history.append(mes) 
        inputs.append(msgCli2)
        outputs.append(mes)
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))

        agents = self.get_agents()
        sys_msg3 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating the list of agents working on a selected project which is stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.        Your main and only job is to provide the name of agent which has to be removed frokm the list of agents currently working on selected project which is consistent with information received in the input message.            
        Your main and only job, is to decide if you should continue editing the list of agents or if no furter edits are needed for the list to be consistent with information in the input message and to answer with one of the following commands associated with your decision:
        - '/keepEditing' to continue changing the list of agents working currently on selected project
        - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
        Please, respond with one of those commands and nothing else."""

        msgCli3 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to update the list of agents working on the project which you've previously selected in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to decide if you should finish editing agents data or do still need to change something in the folowing agents list:
        ----
        {agents}
        ----
        Please, respond with one of those commands and nothing else:
        - '/keepEditing' to continue changing the list of agents working currently on selected project
        - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
        """
        history.append(msgCli3) 
        resp = await neural.askAgent(sys_msg3, inputs, outputs,  msgCli3, 15)
        print(resp)
        data = json.loads(resp)
        decision = data['message']                    
        history.append(decision) 
        inputs.append(msgCli3)
        outputs.append(decision)
        window.write_event_value('-WRITE_COMMAND-', (decision, follow_up))

        if re.search(r'/keepEditing', str(decision)):
            await self.editProjectList(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
        
        else:
            work = str(history)
            history.clear()
            inputs.clear()
            outputs.clear()
            window.write_event_value('-NODE_RESPONSE-', work)
            return work

    async def editProjectList(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement   
        projects = self.get_projects()
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding ongoing projects, which is stored in a local SQL database. It is an operation during which your future responses are being used to 'trigger' functions and/or are recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects, so make sure to not include anything unncecessary in your responses.
        Your main and only job is to deciede what action should be taken in response to incoming message and answer with one of following commands associated with your decision:
        - '/addNewProject' to add new project to the list. Use only (!!!) if that project or a very similar one wasn't already recorded in the database.
        - '/updateProjectData' in order to update/change available information regarding a chosen project of your choice.
        - '/deleteProject' in order to completely erase data associated with a chosen project from the database.
        - anything else will stop the updating process
        Please, respond with one of those commands and nothing else."""          

        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically because of your decision to change/update the data regarding ongoing projects stored in local database and used by multiple agents to coordinate their work in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to decide what action you should take in response to the message above. The current list of all ongoing projects is available here:
        ----
        {projects}
        ----
        If you wish to add new project to the database, make sure if it or a very similar one, isn't already recorded in it. If it is, DO NOT add the same agent for the second time but (if necessary) update data associated with that agent to make it fully consistent with the input message
        Please respond with one of the following commands associated with the action you wish to take:
        - '/addNewProject' to add new project to the list. Use only (!!!) if that project or a very similar one wasn't already recorded in the database.
        - '/updateProjectData' in order to update/change available information regarding a chosen prject of your choice.
        - '/deleteProject' in order to completely erase data associated with a chosen project from the database.
        - anything else will stop the updating process - remember to ALWAYS(!!!) do that if agent which you wanted to add is already assigned to selected project.
        Please, respond with one of those commands and nothing else."""

        history.append(msgCli)
        resp = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 10)
        data = json.loads(resp)
        action = data['message']
        name = data['name']
        msg1 = f"{name}: {action}"
        history.append(action) 
        inputs.append(msgCli)
        outputs.append(action)
        window.write_event_value('-WRITE_COMMAND-', (msg1, follow_up))

        if re.search(r'/addNewProject', str(action)):
            mes = await self.addProject(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            print(mes)

        if re.search(r'/updateProjectData', str(action)):
            mes = await self.editProjectList(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            print(mes)

        if re.search(r'/deleteProject', str(action)):
            mes = await self.removeProject(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            print(mes)

        else:
            mes = "Editing of project list was terminated due to invalid command."
            print(mes)

        history.append(mes) 
        outputs.append(mes)
        window.write_event_value('-WRITE_COMMAND-', (mes, follow_up))

        projects = self.get_projects()
        sys_msg3 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating the information about ongoing projects which is stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.        Your main and only job is to provide the name of agent which has to be removed frokm the list of agents currently working on selected project which is consistent with information received in the input message.            
        Your main and only job, is to decide if you should continue editing the list of agents or if no furter edits are needed for the list to be consistent with information in the input message and to answer with one of the following commands associated with your decision:
        - '/keepEditing' to continue changing the list of agents working currently on selected project
        - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
        Please, respond with one of those commands and nothing else."""

        msgCli3 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to update the data on currently ongoing projects in response to following input message:
        ----
        {msg}
        ----
        Your main and only job is to decide if you should finish editing project's data or do still need to change something in the folowing projects list:
        ----
        {projects}
        ----
        Please, respond with one of those commands and nothing else:
        - '/keepEditing' to continue changing the list of agents working currently on selected project
        - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
        """
        history.append(msgCli3) 
        resp = await neural.askAgent(sys_msg3, inputs, outputs,  msgCli3, 15)
        print(resp)
        data = json.loads(resp)
        decision = data['message']                    
        history.append(decision) 
        inputs.append(msgCli3)
        outputs.append(decision)
        window.write_event_value('-WRITE_COMMAND-', (decision, follow_up))

        if re.search(r'/keepEditing', str(decision)):
            await self.editProjectList(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
        
        else:
            work = str(history)
            history.clear()
            inputs.clear()
            outputs.clear()
            window.write_event_value('-NODE_RESPONSE-', work)
            return work

    async def addFile(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement   
        files = self.get_agents()         
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for adding new files and data associated with them to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        This is the first step of this operation, in which you need to provide name of file which you wish to add to the current list of files utilized by agents in the NeuralGPT framework, by using the incoming message as your context. Your response can't include anything except the name of file you want to add to database."""
        
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to add information about a file to the database in response to following input:
        ----
        {msg}
        ----
        Your main and only job is to provide a name of the file acquired from data provided to you in the message above. It is crucial for you to remember that you respone can't include anything except the file name - as it will be recorded in the database in the original form
        """   

        history.append(msgCli) 
        try:
            response = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 10)
            print(response)
            data = json.loads(response)
            file_name = data['message']
            
            history.append(file_name) 
            inputs.append(msgCli)
            outputs.append(file_name)
            
            window.write_event_value('-WRITE_COMMAND-', (file_name, follow_up))

            sys_msg1 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for adding new files and data associated with them to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            This is the second step of this operation, in which you need to provide the path to file which you wish to add to the current list of files utilized by agents in the NeuralGPT framework, by using the incoming message as your context. Your response can't include anything except the provided path to file which you wish to save in database."""            
            
            msgCli1 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to add a new file to the database in response to following input:
            ----
            {msg}
            ----
            Your main and only job is to provide path to the new file, which you need to acquire from data provided to you in the message above. It is crucial for you to remember that you respone can't include anything except the provided path to file which you wish to save in database."""   
            history.append(msgCli1) 
            response1 = await neural.askAgent(sys_msg1, inputs, outputs, msgCli1, 10)
            print(response1)
            data1 = json.loads(response1)
            path = data1['message']
            history.append(path) 
            inputs.append(msgCli1)
            outputs.append(path)
            
            window.write_event_value('-WRITE_COMMAND-', (path, follow_up))

            sys_msg2 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for adding new files and data associated with them to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            This is the third step of this operation, in which you need to provide a short description of the file which you wish to add to the current list of files utilized by agents in the NeuralGPT framework, by using the incoming message as your context. Your response can't include anything except the provided path to file which you wish to save in database. Remember that the description should be short, simple and include all functions of the file."""
 
            msgCli2 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to add a new file to the database in response to following input:
            ----
            {msg}
            ----
            Your main and only job is to provide a short description of the file content, which you need to acquire from data provided to you in the message above. It is crucial for you to remember that you respone can't include anything except the description of file in question - as it will be recorded in the database in the original form. 
            """
            history.append(msgCli2) 
            response2 = await neural.askAgent(sys_msg2, inputs, outputs, msgCli2, 10)
            print(response2)
            data4 = json.loads(response2)
            description = data4['message']
            agentName = data4['name']
            desc = f"{agentName}: {description}"
            window.write_event_value('-WRITE_COMMAND-', (desc, follow_up))

            sys_msg4 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for adding new files and data associated with them to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            This is the fourth and last step of this operation, in which you need to confirm that the data which you wish to add to the database is consi8stent with tyhe information received in the input message and respond with one of following commands associated with your decision:
            - '/confirmNewFile' to confirm the consistency of data that will be written into the local database.
            - '/cancelOperation' to stop the process of adding new file to local database and to proceed further with the response generation process.
            """
 
            msgCli4 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to add a new file to the local database in response to following input:
            ----
            {msg}
            ----
            Your main and only job is to confirm that data that will be written in the local SQL database is fully consistent with data provided to you in the message above. This is the data that will be recorded in the SQL database:
            - File name: {file_name}
            - File path: {path}
            - File description: {description}
            ----
            To assign the file to an ongoing project, it has to be first saved in the database and then updated it from the file list
            It is crucial for you to remember that your response can't include anything except one of the following commands:
            - '/confirmNewFile' to confirm the consistency of data that will be written into the local database.
            - '/cancelOperation' to stop the process of adding new project to local database and to proceed further with the response generation process.
            Before confirming the operation, make sure that the file whi9ch you want to add to database isn't saved in it already - here is the list of  all recorded files:
            {files}
            ----
            """    

            response4 = await neural.askAgent(sys_msg4, inputs, outputs, msgCli4, 10)
            print(response4)
            data4 = json.loads(response4)
            final = data4['message']
            agentName = data4['name']
            dec = f"{agentName}: {final}"
            window.write_event_value('-WRITE_COMMAND-', (dec, follow_up))
            if re.search(r'/confirmNewFile', str(final)):
                timestamp = datetime.datetime.now().isoformat()
                self.add_file(file_name, path, description)
                conf = f"File successfully added to database (time: {timestamp})"
                window.write_event_value('-WRITE_COMMAND-', (conf, follow_up))
                return conf
            else:
                resp = "Operation was cancelled"
                print(resp)
                return resp

        except Exception as e:
            print(f"Error: {e}")      

    async def addAgent(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement   
        agents = self.get_agents()         
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for adding agents and data associated with them to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        This is the first step of this operation, in which you need to provide name of agent which you wish to add to the current list of agents cooperating within the NeuralGPT framework using the incoming message as your context. Your response can't include anything except the project name of your choice. Remember that the project name should ber short, simple and express the premise of that project."""
        
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to add/modify information about an agent in response to following input:
        ----
        {msg}
        ----
        Your main and only job is to provide a name of the agent acquired from data provided to you in the message above. It is crucial for you to remember that you respone can't include anything except the agent name - as it will be recorded in the database in the original form."""   

        history.append(msgCli) 
        try:
            response = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 10)
            print(response)
            data = json.loads(response)
            agent_name = data['message']
            
            history.append(agent_name) 
            inputs.append(msgCli)
            outputs.append(agent_name)
            
            window.write_event_value('-WRITE_COMMAND-', (agent_name, follow_up))

            sys_msg1 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for adding agents and data associated with them to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            This is the second step of this operation, in which you need to provide the main role/functionality ofr the agent which you wish to add to the current list of agents cooperating within the NeuralGPT framework using the incoming message as your context. Your response can't include anything except a short description of main functions and capabilities of agent you wish to save in database. Remember that the description should be short, simple and include all main functions of an agent."""            
            
            msgCli1 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to add/modify information about an agent recorded in local database in response to following input:
            ----
            {msg}
            ----
            Your main and only job is to provide a short description of the main agent's function within the NeuralGPT framework, which you beed to acquire from data provided to you in the message above. It is crucial for you to remember that you respone can't include anything except the description of main function(s) - as it will be recorded in the database in the original form."""   

            response1 = await neural.askAgent(sys_msg1, inputs, outputs, msgCli1, 10)
            print(response1)
            data1 = json.loads(response1)
            role = data1['message']
            history.append(role) 
            inputs.append(msgCli1)
            outputs.append(role)
            
            window.write_event_value('-WRITE_COMMAND-', (role, follow_up))

            sys_msg4 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for creating/adding new projects to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            This is the fifth and last step of this operation, in which you confirm that data that will be written in the local SQL database is fully consistent with data provided to you in the incoming message. Your response can't include anything except the command associated with your final yes/no decision."""
 
            msgCli4 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to create a new project in the local database in response to following input:
            ----
            {msg}
            ----
            Your main and only job is to confirm that data that will be written in the local SQL database is fully consistent with data provided to you in the message above. This is the data that will be recorded in the SQL database:
            - Agent name: {agent_name}
            - Agent role: {role}
            ----
            To assign new agent to an ongoing project, it has to be first saved in the database and then update the new agent by updating it from thbe agents list
            It is crucial for you to remember that your response can't include anything except one of the following commands:
            - '/confirmNewAgent' to confirm the consistency of data that will be written into the local database.
            - '/cancelOperation' to stop the process of adding new project to local database and to proceed further with the response generation process.
            """    

            response4 = await neural.askAgent(sys_msg4, inputs, outputs, msgCli4, 10)
            print(response4)
            data4 = json.loads(response4)
            final = data4['message']
            agentName = data4['name']
            dec = f"{agentName}: {final}"
            window.write_event_value('-WRITE_COMMAND-', (dec, follow_up))
            if re.search(r'/confirmNewProject', str(final)):
                timestamp = datetime.datetime.now().isoformat()
                self.add_agent(agent_name, role)
                conf = f"Agent successfully added to database (time: {timestamp})"
                window.write_event_value('-WRITE_COMMAND-', (conf, follow_up))
                return conf
            else:
                resp = "Operation was cancelled"
                print(resp)
                return resp

        except Exception as e:
            print(f"Error: {e}")      

    async def addProject(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement        
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for creating/adding new projects to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        This is the first step of this operation, in which you need to provide a name of the new project accordingly to data provided to you in the incoming message. Your response can't include anything except the project name of your choice. Remember that the project name should ber short, simple and express the premise of that project."""
        
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to create a new project in the local database in response to following input:
        ----
        {msg}
        ----
        Your main and only job is to provide a name of the new project accordingly to data provided to you in the message above. It is crucial for you to remember that you respone can't include anything except the project name of your choice - as it will be recorded in the database in the original form. Remember that the project name should ber short, simple and express the premise of that project."""   

        history.append(msgCli) 
        try:
            response = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 10)
            print(response)
            data = json.loads(response)
            project_name = data['message']
            
            history.append(project_name) 
            inputs.append(msgCli)
            outputs.append(project_name)
            
            window.write_event_value('-WRITE_COMMAND-', (project_name, follow_up))

            sys_msg1 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for creating/adding new projects to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            This is the second step of this operation, in which you need to provide short description of the new project accordingly to data provided to you in the incoming message. Your response can't include anything except the project name of your choice. Remember that the project description should be short, simple and clearly express the premise of that project."""
            
            msgCli1 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to create a new project in the local database in response to following input:
            ----
            {msg}
            ----
            Your main and only job is to provide description of the new project accordingly to data provided to you in the message above and the project name chosen in the previous step: {project_name}. It is crucial for you to remember that you respone can't include anything except the project description of the project you are adding - as it will be recorded in the database in the original form. Remember that the project description should ber short, simple and clearly express the premise of that project."""   

            response1 = await neural.askAgent(sys_msg1, inputs, outputs, msgCli1, 10)
            print(response1)
            data1 = json.loads(response1)
            project_description = data1['message']
            history.append(project_description) 
            inputs.append(msgCli1)
            outputs.append(project_description)
            
            window.write_event_value('-WRITE_COMMAND-', (project_description, follow_up))

            sys_msg2 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for creating/adding new projects to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            This is the third step of this operation, in which you need to provide a more detailed plan of completing the new project accordingly to data provided to you in the incoming message. Your response can't include anything except the project plan. Remember that the plan should be clear and describe individual operations ste-by-step, so that later it will be easy to assign agents to particular tasks."""
            
            msgCli2 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to create a new project in the local database in response to following input:
            ----
            {msg}
            ----
            Your main and only job is to provide a more detailed plan of completing the new project accordingly to data provided to you in the message above, project name chosen in the first step: {project_name} and project description defined in previous step: {project_description}. It is crucial for you to remember that the plan should be clear and describe individual operations ste-by-step, so that later it will be easy to assign agents to particular tasks."""   

            if follow_up == 'client':
                response2 = await neural.ask2(sys_msg2, msgCli2, 3500)
            else:
                response2 = await neural.ask(sys_msg2, msgCli2, 3500)
            print(response2)
            data2 = json.loads(response2)
            project_plan = data2['message']
            history.append(project_plan) 
            inputs.append(msgCli2)
            outputs.append(project_plan)
            
            window.write_event_value('-WRITE_COMMAND-', (project_plan, follow_up))   

            sys_msg4 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for creating/adding new projects to a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            This is the fifth and last step of this operation, in which you confirm that data that will be written in the local SQL database is fully consistent with data provided to you in the incoming message. Your response can't include anything except the command associated with your final yes/no decision."""
 
            msgCli4 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to create a new project in the local database in response to following input:
            ----
            {msg}
            ----
            Your main and only job is to confirm that data that will be written in the local SQL database is fully consistent with data provided to you in the message above. This is the data that will be recorded in the SQL database:
            - Project name: {project_name}
            - Project description: {project_description}
            - Project plan:
            ----
            {project_plan}
            ----

            It is crucial for you to remember that your response can't include anything except one of the following commands:
            - '/confirmNewProject' to confirm the consistency of data that will be written into the local database.
            - '/cancelOperation' to stop the process of adding new project to local database and to proceed further with the response generation process.
            """    

            response4 = await neural.askAgent(sys_msg4, inputs, outputs, msgCli4, 10)
            print(response4)
            data4 = json.loads(response4)
            final = data4['message']
            agentName = data4['name']
            dec = f"{agentName}: {final}"
            window.write_event_value('-WRITE_COMMAND-', (dec, follow_up))
            if re.search(r'/confirmNewProject', str(final)):
                timestamp = datetime.datetime.now().isoformat()
                status = f"Project has been created on: {timestamp}"
                self.add_project(project_name, project_description, project_plan, status)
                conf = f"Project successfully added to database (time: {timestamp})"
                return conf
            else:
                resp = "Operation was cancelled"
                print(resp)
                return resp

        except Exception as e:
            print(f"Error: {e}")           

    async def updateFile(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement
        files = self.get_files()    
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data stored in a SQL database regarding local files and their associations. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        This is the first step of this operation, in which you need to provide a name of the file that requires to be updated accordingly to data provided to you in the incoming message. Your response can't include anything except the file name. Remember that the name should be given in it's exact form as it will be used to retrieve/modify data in the database."""
        
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically because of your decision to update data regarding a specific local file that is recorded in the database in response to following input:
        ----
        {msg}
        ----
        Your main and only job is to provide a name of the agent which you want to update accordingly to data provided to you in the message above. It is crucial for you to remember that you respone can't include anything except the file name - as it will be used in original form to retrieve data from a local SQL database. Here is the list of all files available currently in the database:
        ----
        {files}
        ----
        Remember to respond ONLY with the chosen file name in it's exact form, including extension/format (eg. example.txt)."""   

        history.append(msgCli) 
        try:
            response = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 10)
            print(response)
            data = json.loads(response)
            file_name = data['message']
            
            history.append(file_name) 
            inputs.append(msgCli)
            outputs.append(file_name)
            
            window.write_event_value('-WRITE_COMMAND-', (file_name, follow_up))
            file = self.get_file_by_name(file_name)
            print(file)
            window.write_event_value('-WRITE_COMMAND-', (file, follow_up))

            sys_msg1 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data stored in a local SQL database regarding a previously selected file. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            Your main and only job is to respond with one of following commands, associated with the specific set of data you want to change/update. Here are those commands:
            - '/editFileName' to change/update selected file name.
            - '/editFilePath' to change/update the current role/function of selected agent.
            - '/editFileDescription' to change/update description of selected file.
            - '/addFileToProject' to assign selected agent to a chosen project.
            - '/removeFileFromProject' to remove selected agent from the project it's assigned to currently.
            Keep in mind that after each edit/change which you'll make, you will have the option to change another set of recorded data or to finish the ongointg edit/change operation cycle. Renember that your response should include only one of the provided commands and anything else."""
            
            msgCli1 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to modify/update information about selected file in response to following input:
            ----
            {msg}
            ----
            This is the data regarding selected file that is currently available in the project managment database:
            ----
            - File name: {file[1]}
            - File path: {file[2]}
            - File description {file[3]}
            - Project(s) which selected file is associated with: {file[4]}
            ----
            Your main and only job is to respond with one of following commands, associated with the specific set of data you want to change/update. Here are those commands:
            ----
            - '/editFileName' to change/update selected file name.
            - '/editFilePath' to change/update the current role/function of selected agent.
            - '/editFileDescription' to change/update description of selected file.
            - '/addFileToProject' to assign selected agent to a chosen project.
            - '/removeFileFromProject' to remove selected agent from the project it's assigned to currently.
            Keep in mind that after each edit/change which you'll make, you will have the option to change another set of recorded data or to finish the ongointg edit/change operation cycle. Renember that your response should include only one of the provided commands and nothing else."""   

            response1 = await neural.askAgent(sys_msg1, inputs, outputs, msgCli1, 5)
            print(response1)
            data1 = json.loads(response1)
            edit = data1['message']
            history.append(edit) 
            inputs.append(msgCli1)
            outputs.append(edit)
            window.write_event_value('-WRITE_COMMAND-', (edit, follow_up))

            if re.search(r'/editFiletName', str(edit)):
                new_name = await self.updateFileName(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, file_name)
                print(mes)
                file_name = new_name
                
            if re.search(r'/editFilePath', str(edit)):
                mes = await self.updateFilePath(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, file_name)
                print(mes)

            if re.search(r'/editFileDescription', str(edit)):
                mes = await self.updateFileDescription(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, file_name)
                print(mes)

            if re.search(r'/addFileToProject', str(edit)):
                source = 'file'
                mes = await self.addFileToProject(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, file_name, source)
                print(mes)

            if re.search(r'/removeFileFromProject', str(edit)):
                source = 'file'
                mes = await self.removeFileFromProject(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, file_name, source)
                print(mes)

            window.write_event_value('-NODE_RESPONSE-', mes)
            
            file = self.get_file_by_name(file_name)
            sys_msg3 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating the information about selected file which is stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.        Your main and only job is to provide the name of agent which has to be removed frokm the list of agents currently working on selected project which is consistent with information received in the input message.            
            Your main and only job, is to decide if you should continue editing the selected file or if no furter edits are needed for the data to be consistent with information in the input message and to answer with one of the following commands associated with your decision:
            - '/keepEditing' to continue changing the list of agents working currently on selected project
            - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
            Please, respond with one of those commands and nothing else."""

            msgCli3 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to update the information about selected file: {file_name} in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to decide if you should finish editing or do still need to change something in the folowing project information:
            ----
            - File name: {file[1]}
            - File path: {file[2]}
            - File description {file[3]}
            - Project(s) which selected file is associated with: {file[4]}
            ----
            Please, respond with one of those commands and nothing else:
            - '/keepEditing' to continue changing the list of agents working currently on selected project
            - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
            """
            history.append(msgCli3) 
            resp = await neural.askAgent(sys_msg3,  msgCli3, 15)
            print(resp)
            data = json.loads(resp)
            decision = data['message']                    
            history.append(decision) 
            inputs.append(msgCli3)
            outputs.append(decision)
            window.write_event_value('-WRITE_COMMAND-', (decision, follow_up))

            if re.search(r'/keepEditing', str(decision)):
                await self.updateFile(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            
            else:
                work = str(history)
                history.clear()
                inputs.clear()
                outputs.clear()
                window.write_event_value('-NODE_RESPONSE-', work)
                return work

        except Exception as e:
            print(f"Error: {e}")  

    async def updateAgent(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement
        agents = self.get_agents()    
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected project stored in a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        This is the first step of this operation, in which you need to provide a name of the agent that requires to be updated accordingly to data provided to you in the incoming message. Your response can't include anything except the project name of your choice. Remember that the project name should be given in it's exact form as it will be used as input data for Python function."""
        
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically because of your decision to update data regarding a specific agent that is recorded in the local database in response to following input:
        ----
        {msg}
        ----
        Your main and only job is to provide a name of the agent which you want to update accordingly to data provided to you in the message above. It is crucial for you to remember that you respone can't include anything except the agent's name of your choice - as it will be used in original form to retrieve data from a local SQL database. Here is the list of all agents available currently in the database:
        ----
        {agents}
        ----
        Remember to respond ONLY with the chosen agent's name."""   

        history.append(msgCli) 
        try:
            response = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 10)
            print(response)
            data = json.loads(response)
            agent_name = data['message']
            
            history.append(agent_name) 
            inputs.append(msgCli)
            outputs.append(agent_name)
            
            window.write_event_value('-WRITE_COMMAND-', (agent_name, follow_up))
            agent = self.get_agent_by_name(agent_name)
            print(agent)
            window.write_event_value('-WRITE_COMMAND-', (agent, follow_up))

            sys_msg1 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected project stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            Your main and only job is to respond with one of following commands, associated with the specific set of data you want to change/update. Here are those commands:
            - '/editAgentName' to change/update selected agent's name.
            - '/editAgentRole' to change/update the current role/function of selected agent.
            - '/addAgentToProject' to assign selected agent to a chosen project.
            - '/removeAgentFromProject' to remove selected agent from the project it's assigned to currently.
            Keep in mind that after each edit/change which you'll make, you will have the option to change another set of recorded data or to finish the ongointg edit/change operation cycle. Renember that your response should include only one of the provided commands and anything else."""
            
            msgCli1 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to modify/update information about selected agent in response to following input:
            ----
            {msg}
            ----
            This is the data regarding selected agent that is currently available in the project managment database:
            ----
            - Agent's name: {agent[1]}
            - Agent's role/function: {agent[2]}
            - Project(s) which selected agent is assigned to: {agent[3]}
            ----
            Your main and only job is to respond with one of following commands, associated with the specific set of data you want to change/update. Here are those commands:
            ----
            - '/editAgentName' to change/update selected agent's name.
            - '/editAgentRole' to change/update the current role/function of selected agent.
            - '/addAgentToProject' to assign selected agent to a chosen project.
            - '/removeAgentFromProject' to remove selected agent from the project it's assigned to currently.
            Keep in mind that after each edit/change which you'll make, you will have the option to change another set of recorded data or to finish the ongointg edit/change operation cycle. Renember that your response should include only one of the provided commands and nothing else."""   

            response1 = await neural.askAgent(sys_msg1, inputs, outputs, msgCli1, 5)
            print(response1)
            data1 = json.loads(response1)
            edit = data1['message']
            history.append(edit) 
            inputs.append(msgCli1)
            outputs.append(edit)
            window.write_event_value('-WRITE_COMMAND-', (edit, follow_up))

            if re.search(r'/editAgentName', str(edit)):
                new_name = await self.updateAgentName(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, agent_name)
                print(mes)
                agent_name = new_name
                
            if re.search(r'/editAgentRole', str(edit)):
                mes = await self.updateAgentRole(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, agent_name)
                print(mes)

            if re.search(r'/addAgentToProject', str(edit)):
                mes = await self.assignAgentToProject(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, agent_name)
                print(mes)

            if re.search(r'/removeAgentFromProject', str(edit)):
                mes = await self.removeAgentFromProject(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, agent_name)
                print(mes)

            window.write_event_value('-NODE_RESPONSE-', mes)
            
            agent = self.get_agent_by_name(agent_name)
            sys_msg3 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating the list of agents working on a selected project which is stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.        Your main and only job is to provide the name of agent which has to be removed frokm the list of agents currently working on selected project which is consistent with information received in the input message.            
            Your main and only job, is to decide if you should continue editing the list of agents or if no furter edits are needed for the list to be consistent with information in the input message and to answer with one of the following commands associated with your decision:
            - '/keepEditing' to continue changing the list of agents working currently on selected project
            - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
            Please, respond with one of those commands and nothing else."""

            msgCli3 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to update the list of agents working on the project which you've previously selected in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to decide if you should finish editing project's data or do still need to change something in the folowing project information:
            ----
            - Agent's name: {agent[1]}
            - Agent's role/function: {agent[2]}
            - Project(s) which selected agent is assigned to: {agent[3]}
            ----
            Please, respond with one of those commands and nothing else:
            - '/keepEditing' to continue changing the list of agents working currently on selected project
            - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
            """
            history.append(msgCli3) 
            resp = await neural.askAgent(sys_msg3,  msgCli3, 15)
            print(resp)
            data = json.loads(resp)
            decision = data['message']                    
            history.append(decision) 
            inputs.append(msgCli3)
            outputs.append(decision)
            window.write_event_value('-WRITE_COMMAND-', (decision, follow_up))

            if re.search(r'/keepEditing', str(decision)):
                await self.updateAgent(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            
            else:
                work = str(history)
                history.clear()
                inputs.clear()
                outputs.clear()
                window.write_event_value('-NODE_RESPONSE-', work)
                return work

        except Exception as e:
            print(f"Error: {e}")  

    async def updateProject(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):
        if gui == 'PySimpleGUI':
            window = UIelement
        projectList = self.get_projects()    
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected project stored in a local SQL database. It is a multi-step operation during which your responses will be recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
        This is the first step of this operation, in which you need to provide a name of the project which you want to update accordingly to data provided to you in the incoming message. Your response can't include anything except the project name of your choice. Remember that the project name should be given in it's exact form as it will be used as input data for Python function."""
        
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically because of your decision to update data regarding a project recorded in the local database in response to following input:
        ----
        {msg}
        ----
        Your main and only job is to provide a name of the project which you want to update accordingly to data provided to you in the message above. It is crucial for you to remember that you respone can't include anything except the project name of your choice - as it will be recorded in the database in the original form. Remember that the project name should be given in it's exact form as it will be used as input data for Python function. Here is the list of all projects available currently in the database:
        ----
        {projectList}
        """   

        history.append(msgCli) 
        try:
            response = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 10)
            print(response)
            data = json.loads(response)
            project_name = data['message']
            
            history.append(project_name) 
            inputs.append(msgCli)
            outputs.append(project_name)
            
            window.write_event_value('-WRITE_COMMAND-', (project_name, follow_up))
            project = self.get_project_by_name(project_name)
            print(project)

            sys_msg1 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating data regarding a selected project stored in a local SQL database. It is an operation during which your future responses are being recorded in their exact form in the database and used by other agents to coordinate their work on large-scale projects.
            Your main and only job is to respond with one of following commands, associated with the specific set of data you want to change/update. Here are those commands:
            - '/editProjectName' to change/update the current project name.
            - '/editProjectDescription' to change/update the current project description.
            - '/editProjectPlan' to change/update the current project plan.
            - '/editAgentList' to change/update the current list of agents working on the project.
            - '/editFileList' to change/update the current list of local files associated with the project.
            - '/editProjectStatus' to change/update the current project status.
            Keep in mind that after each edit/change which you'll make, you will have the option to change another set of recorded data or to finish the ongointg edit/change operation cycle. Renember that your response should include only one of the provided commands and anything else.
            """
            
            msgCli1 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to modify/update data regarding a selected project stored in a local SQL database in response to following input:
            ----
            {msg}
            ----
            - Project name: {project_name}
            - Project description: {project[2]}
            - Project plan: {project[3]}
            - Agents working on the project: {project[4]}
            - Local files associated with the project: {project[5]}
            - Current status of the project: {project[6]}
            ----
            Your main and only job is to respond with one of following commands, associated with the specific set of data you want to change/update. Here are those commands:
            - '/editProjectName' to change/update the current project name.
            - '/editProjectDescription' to change/update the current project description.
            - '/editProjectPlan' to change/update the current project plan.
            - '/editAgentList' to change/update the current list of agents working on the project.
            - '/editFileList' to change/update the current list of local files associated with the project.
            - '/editProjectStatus' to change/update the current project status.
            Keep in mind that after each edit/change which you'll make, you will have the option to change another set of recorded data or to finish the ongointg edit/change operation cycle. Renember that your response should include only one of the provided commands and anything else.

            provide description of the new project accordingly to data provided to you in the message above and the project name chosen in the previous step: {project_name}. It is crucial for you to remember that you respone can't include anything except the project description of the project you are adding - as it will be recorded in the database in the original form. Remember that the project description should ber short, simple and clearly express the premise of that project."""   

            response1 = await neural.askAgent(sys_msg1, inputs, outputs, msgCli1, 5)
            print(response1)
            data1 = json.loads(response1)
            edit = data1['message']
            history.append(edit) 
            inputs.append(msgCli1)
            outputs.append(edit)
            window.write_event_value('-WRITE_COMMAND-', (edit, follow_up))

            if re.search(r'/editProjectName', str(edit)):
                new_name = await self.editProjectName(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, project_name)
                print(new_name)
                project_name = new_name

            if re.search(r'/editProjectDescription', str(edit)):
                mes = await self.editProjectDescription(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, project_name)
                print(mes)

            if re.search(r'/editProjectPlan', str(edit)):
                mes = await self.editProjectPlan(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, project_name)
                print(mes)

            if re.search(r'/editAgentList', str(edit)):
                mes = await self.editAgentList(self, UIelement, gui, follow_up, neural, history, inputs, outputs, msg, project_name)
                print(mes)
            
            if re.search(r'/editFileList', str(edit)):
                mes = await self.editFileList(self, UIelement, gui, follow_up, neural, history, inputs, outputs, msg, project_name)
                print(mes)

            if re.search(r'/editProjectStatus', str(edit)):
                mes = await self.editProjectStatus(UIelement, gui, neural, history, inputs, outputs, msg, follow_up, project_name)
                print(mes)

            window.write_event_value('-NODE_RESPONSE-', mes)

            project = self.get_project_by_name(project_name)
            sys_msg3 = f"""You are temporarily working as an autonomous decision-making 'module' responsible for updating the list of agents working on a selected project which is stored in a local SQL database. Be sure that data recorded by you in the database is correct as it will be used by other agents to coordinate their work on large-scale projects.        Your main and only job is to provide the name of agent which has to be removed frokm the list of agents currently working on selected project which is consistent with information received in the input message.            
            Your main and only job, is to decide if you should continue editing the list of agents or if no furter edits are needed for the list to be consistent with information in the input message and to answer with one of the following commands associated with your decision:
            - '/keepEditing' to continue changing the list of agents working currently on selected project
            - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
            Please, respond with one of those commands and nothing else."""

            msgCli3 = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to update the list of agents working on the project which you've previously selected in response to following input message:
            ----
            {msg}
            ----
            Your main and only job is to decide if you should finish editing project's data or do still need to change something in the folowing project information:
            ----
            - Project name: {project_name}
            - Project description: {project[2]}
            - Project plan: {project[3]}
            - Agents working on the project: {project[4]}
            - Local files associated with the project: {project[5]}
            - Current status of the project: {project[6]}
            ----
            Please, respond with one of those commands and nothing else:
            - '/keepEditing' to continue changing the list of agents working currently on selected project
            - '/stopEditing' to finish editing the agent list and ssend back answer to the source of the initual input message.
            """
            history.append(msgCli3) 
            resp = await neural.askAgent(sys_msg3,  msgCli3, 15)
            print(resp)
            data = json.loads(resp)
            decision = data['message']                    
            history.append(decision) 
            inputs.append(msgCli3)
            outputs.append(decision)
            window.write_event_value('-WRITE_COMMAND-', (decision, follow_up))

            if re.search(r'/keepEditing', str(decision)):
                await self.updateAgent(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
            
            else:
                work = str(history)
                history.clear()
                inputs.clear()
                outputs.clear()
                window.write_event_value('-NODE_RESPONSE-', work)
                return work

        except Exception as e:
            print(f"Error: {e}")  

    async def SQLagent(self, UIelement, gui, neural, history, inputs, outputs, msg, follow_up):        
        if gui == 'PySimpleGUI':
            window = UIelement
        projectList = self.get_projects()
        sys_msg = f"""You are temporarily working as an autonomous decision-making 'module' responsible for performing operations on a local SQL database including most important information about current and future projects and agants cooperating in the NeuralGPT framework. Your main and only job is to decide what action should be taken in response to a given input by answering with a proper command-function associated with action which you want to take. Those are the available command-functions and actions associated with them:
        - '/getProjectList' to get a list of all proects recorded in the database.
        - '/getAgentList' to get a list of all agents recorded in the database.
        - '/getFileList' to get a list of all files recorded in the database.
        - '/updateProjects' to change data related to currently ongoing projects.
        - '/updateAgents' to modify the current list of agents and their associations with particular projects.
        - '/updateFiles' to modify the current list of files and their associations with particular projects.
        It is crucial for you to respond only with one of those command-functions in their exact forms and nothing else, as those phrases are being used to 'trigger' desired functions - that's why the number of tokens in your response will be limited to 5. It is crucial for you to respond only with one of those 5 command-functions in their exact forms and nothing else, as those phrases are being used to 'trigger' desired functions - that's why the number of tokens in your response will be limited to 5.
        """
        msgCli = f"""SYSTEM MESSAGE: This message was generated automatically in response to your decision to take a particular action/operation in response to following input:
        ----
        {msg}
        ----
        Before you take any action, you need also know the list of projects existing already in the local database - here it is (it might be empty if no previous projects have been recorded):
        ----
        {projectList}
        ----  
        You have the capability to take practical actions (do work) in response to inputs by answering with a proper command-function associated with the action which you want to perform from thoswe available for you to take:
        - '/getProjectList' to get a list of all proects recorded in the database.
        - '/getAgentList' to get a list of all agents recorded in the database.
        - '/getFileList' to get a list of all files recorded in the database.
        - '/updateProjects' to change data related to currently ongoing projects.
        - '/updateAgents' to modify the current list of agents and their associations with particular projects.
        - '/updateFiles' to modify the current list of files and their associations with particular projects.
        It is crucial for you to respond only with one of those command-functions in their exact forms and nothing else.
        """     
        history.append(msgCli) 
        try:
            response = await neural.askAgent(sys_msg, inputs, outputs, msgCli, 5)
            print(response)
            data = json.loads(response)

            if window['-USE_NAME-'].get():
                srv_name = window['-AGENT_NAME-'].get()
            else:    
                srv_name = data['name']
            decision = data['message']
            timestamp = datetime.datetime.now().isoformat()
            srv_text = f"{srv_name}: {decision} (time: {timestamp})"
            
            history.append(srv_text) 
            inputs.append(msgCli)
            outputs.append(srv_text)
            
            window.write_event_value('-WRITE_COMMAND-', (srv_text, follow_up))

            if re.search(r'/getProjectList', str(decision)):
                resp = self.get_projects()
                print(resp)

            if re.search(r'/getAgentList', str(decision)):
                resp = self.get_agents()
                print(resp)

            if re.search(r'/getFileList', str(decision)):
                resp =  self.get_files()
                print(resp)

            if re.search(r'/updateProjects', str(decision)):
                resp = await self.editProjectList(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
                print(resp)

            if re.search(r'/updateAgents', str(decision)):
                resp = await self.editAgentList(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
                print(resp)
            
            if re.search(r'/updateFiles', str(decision)):
                resp = await self.editFileList(UIelement, gui, neural, history, inputs, outputs, msg, follow_up)
                print(resp)

            else:
                resp = response

            window.write_event_value('-NODE_RESPONSE-', resp)
            return resp   

        except Exception as e:
            print(f"Error: {e}")   