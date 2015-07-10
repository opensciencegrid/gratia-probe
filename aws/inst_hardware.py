#!/usr/bin/env python
from pprint import pprint
import datetime;

class insthardware:
	def __init__(self,filelocation):
		self.fileloc=filelocation
	def gettypedetails(self):	
		types=[]
		field=[]
		#repo = {}
		
		infile = open(self.fileloc,'r')
		firstline = infile.readline()
		fields=firstline.split("\t")
		print fields
		for f in fields:
			#print f
			if f == "\n":
				fields.remove(f)
	
			print fields
		lines= infile.readlines()
		print firstline
		for i in lines:
			print i	
			values=i.split("\t")
			values.remove("\n")
			print values
			x=0
			repo={}
			while x<len(fields):
				repo[fields[x]]=values[x]
				x+=1
			print repo
			types.append(repo)
		pprint(types)
		return types

	#module = ''.join(i.split(',')[:-1])
	#time = ''.join(i.split(',')[1:]).replace('\n','')
	#if not module in repo: 
	#	repo[module] = time
