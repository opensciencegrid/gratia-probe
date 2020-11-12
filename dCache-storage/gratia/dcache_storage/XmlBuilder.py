from __future__ import print_function

import sys,os

from xml.sax import saxutils
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
from xml.sax.handler import feature_namespaces

class TestObject:
   def __init__(self):
       pass

   def methodA(self,b):
       self.b = b

   def methodB(self,c):
       self.c = c

   def foo(self):
       print("Foo:",self.b)

class Result:
   def __init__(self):
       pass

   def setArray(self,o):
       self._o = o
   def get(self):
       return self._o

testStr = """<TestObject><methodA>23</methodA><methodB><array><TestObject/><TestObject><methodA>inside</methodA></TestObject><TestObject/></array></methodB></TestObject>"""

class SaxParser:

   _parser = None

   def getSaxParser(self):

        if SaxParser._parser:
          return SaxParser._parser

        SaxParser._parser = make_parser()
        SaxParser._parser.setFeature(feature_namespaces, 0)

        return SaxParser._parser

   def parse(self,contenthandler,fd):
       self.getSaxParser().setContentHandler(contenthandler)
       self.getSaxParser().parse(fd)

class Node:
    def __init__(self,node,text):
       self.node = node
       self.text = text
    def __str__(self):
       return str(self.node)+","+self.text

class Xml2ObjectBuilder(ContentHandler):

    def __init__(self,fd ):

        self._root = None
        self._attrs = None
        self._content = []
        self._state = [1]  # 1 create content , 0 set methods

        SaxParser().parse(self,fd)

    def startElement(self, name, attrs):
        if ( self._state[-1] == 1 ):
           if ( name == "array" ):
              current = []
              self._state.append(1)
           else:
              pos = name.rfind('.')
              if ( pos != -1 ):
                exec("import "+name[:pos])
              exec("current = "+name+"()")
              self._state.append(0)
      
           if ( self._root != None ):
                 self._content.append(self._root)

           self._root = Node(current,None)
        else:
           self._state.append(1)
           if ( self._root != None ):
                 self._content.append(self._root)

        self._attrs = attrs
        


    def endElement(self, name):
          state = self._state.pop()
          if ( state == 1): # state machine has been creating content, which should be self._root, current level self._content.pop
             if ( name != "array" ): # array is not an method , skip it
                content = self._content.pop()

                if ( self._root == content ): #true for terminal elements only
                   value = self._root.text
                   self._root.text = None
                else:
                   value = self._root.node

                if ( self._attrs != None and 'type' in self._attrs ):
                   if (  self._attrs['type'] == 'numeric' ):
                      value = float(value)

                self._attrs = None

                getattr(content.node,name)(value)
                self._root = content
          else:
             if ( len(self._content) > 0 and type(self._content[-1].node) == list ):
               content = self._content.pop()
               content.node.append(self._root.node)
               self._root = content

    def characters(self,content):
        if ( self._state[-1] == 1 ):
           if ( self._root.text == None ):
              self._root.text = content
           else:
              self._root.text = self._root.text + content

    def get(self):
        return self._root.node

if __name__ == '__main__':
  import sys

  fileName = sys.argv[1]
  print(fileName)
  f = file(fileName)
  pyO = Xml2ObjectBuilder(f)
  print(pyO.get().b)

