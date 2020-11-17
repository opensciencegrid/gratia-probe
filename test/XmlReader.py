#!/usr/bin/env python

from __future__ import print_function

import os, sys
from xml.dom.minidom import parse

indentLevel = 0
def TreePrint(xmlDoc, node):
    global indentLevel
    indent = ' ' * indentLevel
    if not node: node = xmlDoc.documentElement
    print(indent, "nodeType:  ", node.nodeType)
    print(indent, "namespace: ", node.namespaceURI)
    print(indent, "nodeName:  ", node.nodeName)
    print(indent, "nodeValue: ", node.nodeValue)
    print(indent, "nChildren: ", node.childNodes.length)
    indentLevel += 2
    for childNode in node.childNodes:
        TreePrint(xmlDoc, childNode)
    indentLevel -= 2
    
if __name__ == '__main__':

    try:
        xmlDoc = parse(sys.argv[1]);
    except Exception as e:
        print("Execption, \"", e, "\" parsing ", sys.argv[1])
        sys.exit(1)

    # TreePrint(xmlDoc, xmlDoc.documentElement)

    print("Trying to find KeyInfo node ... ")
    node = xmlDoc.getElementsByTagNameNS('http://www.w3.org/2000/09/xmldsig#','KeyInfo')

    keyInfoNS = 'http://www.w3.org/2000/09/xmldsig#'
    keyInfoNodes = xmlDoc.getElementsByTagNameNS(keyInfoNS, 'KeyInfo')
    if not keyInfoNodes:
        print("KeyInfo node not found: creating ...")
        keyInfoNode = xmlDoc.createElementNS(keyInfoNS,'ds:KeyInfo')
        keyInfoNode.setAttribute('xmlns:ds', keyInfoNS) # Namespace prefix definition
        print(keyInfoNode.parentNode)
        xmlDoc.documentElement.appendChild(keyInfoNode)

    print(xmlDoc.toxml())
    TreePrint(xmlDoc, xmlDoc.documentElement)

    

