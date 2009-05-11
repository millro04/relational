# -*- coding: utf-8 -*-
# Relational
# Copyright (C) 2009  Salvo "LtWorf" Tomaselli
# 
# Relation is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
# author Salvo "LtWorf" Tomaselli <tiposchi@tiscali.it>

'''This module contains functions to perform various optimizations on the expression trees.
The list general_optimizations contains pointers to general functions, so they can be called
within a cycle.'''

import optimizer

def duplicated_select(n):
    changes=0
    '''This function locates and deletes things like
    σ a ( σ a(C)) and the ones like σ a ( σ b(C))'''
    if n.name=='σ' and n.child.name=='σ':        
        if n.prop != n.child.prop: #Nested but different, joining them
            n.prop = n.prop + " and " + n.child.prop
        n.child=n.child.child
        changes=1
        changes+=duplicated_select(n)
        

    #recoursive scan
    if n.kind==optimizer.UNARY:
        changes+=duplicated_select(n.child)
    elif n.kind==optimizer.BINARY:
        changes+=duplicated_select(n.right)
        changes+=duplicated_select(n.left)
    return changes

def down_to_unions_subtractions_intersections(n):
    '''This funcion locates things like σ i==2 (c ᑌ d), where the union
    can be a subtraction and an intersection and replaces them with
    σ i==2 (c) ᑌ σ i==2(d).   
    '''
    changes=0
    _o=('ᑌ','-','ᑎ')
    if n.name=='σ' and n.child.name in _o:
        
        left=optimizer.node()
        left.prop=n.prop
        left.name=n.name
        left.child=n.child.left
        left.kind=optimizer.UNARY
        right=optimizer.node()
        right.prop=n.prop
        right.name=n.name
        right.child=n.child.right
        right.kind=optimizer.UNARY
        
        n.name=n.child.name
        n.left=left
        n.right=right
        n.child=None
        n.prop=None
        n.kind=optimizer.BINARY
        changes+=1
    
    #recoursive scan
    if n.kind==optimizer.UNARY:
        changes+=down_to_unions_subtractions_intersections(n.child)
    elif n.kind==optimizer.BINARY:
        changes+=down_to_unions_subtractions_intersections(n.right)
        changes+=down_to_unions_subtractions_intersections(n.left)
    return changes

def duplicated_projection(n):
    '''This function locates thing like π i ( π j (R)) and replaces
    them with π i (R)'''
    changes=0
    
    
    if n.name=='π' and n.child.name=='π':
        n.child=n.child.child
        changes+=1
    
    #recoursive scan
    if n.kind==optimizer.UNARY:
        changes+=duplicated_projection(n.child)
    elif n.kind==optimizer.BINARY:
        changes+=duplicated_projection(n.right)
        changes+=duplicated_projection(n.left)
    return changes

def selection_inside_projection(n):
    '''This function locates things like  σ j (π k(R)) and
    converts them into π k(σ j (R))'''
    #TODO Document this in the wiki.
    
    changes=0
    
    if n.name=='σ' and n.child.name=='π':
        changes=1
        temp=n.prop
        n.prop=n.child.prop
        n.child.prop=temp
        n.name='π'
        n.child.name='σ'
    
    #recoursive scan
    if n.kind==optimizer.UNARY:
        changes+=selection_inside_projection(n.child)
    elif n.kind==optimizer.BINARY:
        changes+=selection_inside_projection(n.right)
        changes+=selection_inside_projection(n.left)
    return changes

def subsequent_renames(n):
    '''This function removes redoundant subsequent renames'''
    changes=0
    
    if n.name=='ρ' and n.child.name==n.name:
        changes=1
        
        
        print "PROP",n.prop,"==========",n.child.prop
        n.prop+=','+n.child.prop
        
        _vars={}
        for i in n.prop.split(','):
            q=i.split('➡')
            _vars[q[0].strip()]=q[1].strip()
        n.child=n.child.child
        print _vars
        for i in list(_vars.keys()):
            print i
            if _vars[i] in _vars.keys():
                #Double rename on attribute
                print "i:%s\tvars[i]:%s\t_vars[_vars[i]]: %s\n" % (i,_vars[i],_vars[_vars[i]])
                _vars[i] =  _vars[_vars[i]]
                _vars.pop(i)
        n.prop=""
        print _vars
        for i in _vars.items():
            n.prop+="%s➡%s," % (i[0],i[1])
        n.prop=n.prop[:-1] #Removing ending comma     
    #recoursive scan
    if n.kind==optimizer.UNARY:        
        changes+=subsequent_renames(n.child)
    elif n.kind==optimizer.BINARY:
        changes+=subsequent_renames(n.right)
        changes+=subsequent_renames(n.left)
    return changes


general_optimizations=[duplicated_select,down_to_unions_subtractions_intersections,duplicated_projection,selection_inside_projection,subsequent_renames]
