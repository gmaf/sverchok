# This file is part of project Sverchok. It's copyrighted by the contributors
# recorded in the version control history of the file, available from
# its original location https://github.com/nortikin/sverchok/commit/master
#  
# SPDX-License-Identifier: GPL3
# License-Filename: LICENSE

import bpy
import numpy as np
import wave
# import mathutils
# from mathutils import Vector
# from bpy.props import FloatProperty, BoolProperty
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode

MAX_SOCKETS = 6
DATA_SOCKET = 'SvStringsSocket'


class SvWaveformViewerOperator(bpy.types.Operator):
    bl_idname = "node.waveform_viewer_callback"
    bl_label = "Waveform Viewer Operator"

    idname = bpy.props.StringProperty(default='')
    idtree = bpy.props.StringProperty(default='')
    fn_name = bpy.props.StringProperty(default='')

    def execute(self, context):
        node = bpy.data.node_groups[self.idtree].nodes[self.idname]
        getattr(node, self.fn_name)()
        return {'FINISHED'}

# missing "node.waveform_viewer_dirpick"


class SvWaveformViewer(bpy.types.Node, SverchCustomTreeNode):
    
    """
    Triggers: SvWaveformViewer
    Tooltip: 
    
    A short description for reader of node code
    """


    bl_idname = 'SvWaveformViewer'
    bl_label = 'SvWaveformViewer'
    bl_icon = 'GREASEPENCIL'


    def update_socket_count(self, context):
        ... # if self.num_channels < MAX_SOCKETS 


    num_channels: bpy.props.IntProperty(
        name='num channels', default=1, min=1, max=MAX_SOCKETS,
        description='num channels interleaved', update=update_socket_count)

    bits: bpy.props.IntProperty(name='bit rate', default=16, min=4, max=192)

    sample_rate: bpy.props.IntProperty(
        name="sample rate", min=8000, default=48000)

    auto_normalize: bpy.props.BoolProperty(
        name="normalize")

    colour_limits: bpy.props.BoolProperty(
        name="color limits")

    multi_channel_sockets: bpy.props.BoolProperty(
        name="multiplex", update=updateNode, description="sockets carry multiple layers of data")

    dirname: bpy.props.StringProperty()
    filename: bpy.props.StringProperty()

    def sv_init(self, context):
        self.inputs.new(DATA_SOCKET, 'channel 0')
        self.inputs.new(DATA_SOCKET, 'channel 1')

    def draw_buttons(self, context, layout):
        col = layout.column(align=True)
        
        col.prop(self, 'num_channels')
        col.prop(self, 'sample_rate')
        col.prop(self, 'bits')
        
        col.separator()
        row1 = col.row()
        row1.prop(self, 'auto_normalize', toggle=True)
        row1.prop(self, 'multi_channel_sockets', toggle=True)
        
        col.separator()
        col.prop(self, 'colour_limits')
        
        col.separator()
        cb = "node.waveform_viewer_callback"
        op = self.wrapper_tracked_ui_draw_op(col, cb, icon='CURSOR', text='WRITE')
        op.fn_name = "process_wave"

        col.separator()
        row = col.row(align=True)
        row.prop(self, 'dirname')
        cb = "node.waveform_viewer_dirpick"
        op = self.wrapper_tracked_ui_draw_op(row, cb, icon='FILE', text='')
        op.fn_name = "set_dir"
        col.prop(self, "filename")

    def process(self):
        ...

    def process_wave(self):
        print('process wave pressed')


    def set_dir(self):
        ...





classes = [SvWaveformViewer, SvWaveformViewerOperator]
register, unregister = bpy.utils.register_classes_factory(classes)
