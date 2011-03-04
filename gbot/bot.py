#!/usr/bin/env python
"""
bot.py - Goshubot
Copyright 2011 Daniel Oakley <danneh@danneh.net>

http://danneh.net/maid/
"""

from gbot.modules import ModuleLoader
import os
import sys

class Bot(object):
	""" Handles Bot operations."""
	
	def __init__(self, server, prefix='.', password='uhuehuehue', indent=3):
		""" Sets up bot."""
		self.server = server
		
		self.prefix = prefix
		self.password = password
		self.indent = indent
		
		self.module = None
		self.modules = {}
		self.commands = {}
		
		self.load('modules')
	
	def load(self, path):
		""" Loads modules."""
		for module in ModuleLoader(path):
			self.append(module)
	
	def append(self, module):
		""" Appends a module to the bot."""
		module.gbot = self
		self.modules[module.name] = module
		for alias in module.commands:
			self.commands[alias] = module.commands[alias]
	
	def handle(self, connection, event):
		""" Handle messages"""
		if event.arguments()[0].split(self.prefix)[0] == '': #command for us
			command = event.arguments()[0].split(self.prefix)[1].split(' ')[0]
			
			arg_offset = 0
			arg_offset += len(self.prefix)
			arg_offset += len(command)
			try:
				event.arguments()[0].split(self.prefix)[1].split(' ')[1]
				arg_offset += 1
			except:
				pass
			
			arg = ''
			arg += event.arguments()[0][arg_offset:]
			
			try:
				self.commands[command](arg, connection, event)
			except:
				print 'Bot handle: fail'
				print ' command:',command
				print ' arg:',arg
				#print ' arg_offset:',arg_offset
	
	def quit(self, message):
		""" Quits, may accept a server/channel name later on, once it can join
		    multiple servers/channels."""
		self.server.disconnect(message)
