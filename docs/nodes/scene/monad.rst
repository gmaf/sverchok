Monad
=====

Functionality
-------------

    Warning: This feature is a work in progress in 2.8+. Expect stuff to be broken and breakages during usage.
    -- zeffii

This node encapsulates several selected nodes (Ctrl+G) into a single node, similar to a shadertree node group. 

There are two parts to this node, 
 
 - (Monad) the outer node shell "Monad", this Node is dynamically defined with new properties and sockets whenever required by the Tree inside.
 - (Tree) the internal node tree, with its own input and output nodes. Interaction with the input and output nodes will update the "Monad" shell.

When editing the Tree you can 

 - rearrange sockets
 - rename sockets
 - set slider limits
 - change socket types

Parameters
----------

The UI hints at a few fundamental features of the Monad:

 - Vectorize , Vectorize with Split
 - Loop n times

*Vectorize* tries to match incoming datastreams by repeating data in those sockets that don't have the same number of internal lists.

*Vectorize with Split*
The more complicated this gets, the harder it is to explain in text. Please see some examples below.

*Loop n times*
This can be used for repeatedly applying an effect to a mesh, the number of iteration is currently only configurable via the node UI - it's too easy to accidentally grind your computer to a halt if that was set dynamically via an input socket.


Inputs and Outputs
------------------

Are entirely defined by the Tree that Monad encapsulates


Example of usage
----------------

The github issue tracker has many issues (question and answers) regarding this node, it's a good place to start.

