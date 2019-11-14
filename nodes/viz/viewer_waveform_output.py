# This file is part of project Sverchok. It's copyrighted by the contributors
# recorded in the version control history of the file, available from
# its original location https://github.com/nortikin/sverchok/commit/master
#  
# SPDX-License-Identifier: GPL3
# License-Filename: LICENSE

import os
import numpy as np
import wave
import struct

import bpy
import blf
import bgl
import gpu
from gpu_extras.batch import batch_for_shader

# import mathutils
from mathutils import Vector
# from bpy.props import FloatProperty, BoolProperty
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode, node_id
from sverchok.ui import bgl_callback_nodeview as nvBGL

MAX_SOCKETS = 6
DATA_SOCKET = 'SvStringsSocket'

"""
grid shader borrowed from : https://stackoverflow.com/a/24792822/1243487

"""

grid_vertex_shader = '''
    in vec2 pos;

    void main()
    {
        gl_Position = vec4(pos.x, pos.y, 0.0, 1.0);
    }

'''

grid_fragment_shader = '''

    // uniform float vpw;
    // uniform float vph;
    uniform vec2 offset;
    uniform vec2 pitch;

    void main()
    {
        float vpw = 30.0;
        float vph = 40.0;
        float scaleFactor = 10.0;

        float offX = (scaleFactor * offset[0]) + gl_FragCoord.x;
        float offY = (scaleFactor * offset[1]) + (1.0 - gl_FragCoord.y);

        if (int(mod(offX, pitch[0])) == 0 || int(mod(offY, pitch[1])) == 0) {
            gl_FragColor = vec4(0.0, 0.0, 0.0, 0.5);
        } else {
            gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
        }
    }

'''

class gridshader():
    def __init__(self, w, h, loc):
        x, y = loc
        self.w = w
        self.h = h
        self.vertex_shader = grid_vertex_shader
        self.fragment_shader = grid_fragment_shader
        self.background_coords = [(x, y), (x + w, y), (w + x, y - h), (x, y - h)]
        self.background_indices = [(0, 1, 2), (0, 2, 3)]

def advanced_grid_xy(x, y, args):
    """ 
    x and y are passed by default so you could add font content 
    """
    geom, config = args
    # matrix = context.region_data.perspective_matrix

    print('w', config.grid.w)
    print('h', config.grid.h)
    print('bc', config.grid.background_coords)
    print('bi', config.grid.background_indices)
    print('vs', config.grid.vertex_shader)
    print('fs', config.grid.fragment_shader)

    shader = gpu.types.GPUShader(config.grid.vertex_shader, config.grid.fragment_shader)
    batch = batch_for_shader(shader, 'TRIS', {"pos": config.grid.background_coords}, indices=config.grid.background_indices)
    
    shader.bind()
    # shader.uniform_float("u_mvp", matrix)
    # shader.uniform_float("vpw", config.grid.w)
    # shader.uniform_float("vph", config.grid.h)
    shader.uniform_float("offset", [0.2, 0.4])
    shader.uniform_int("pitch", [20, 20])
    batch.draw(shader)


class NodeTreeGetter():
    __annotations__ = {}
    __annotations__['idname'] = bpy.props.StringProperty(default='')
    __annotations__['idtree'] = bpy.props.StringProperty(default='')

    def get_node(self):
        return bpy.data.node_groups[self.idtree].nodes[self.idname]


class SvWaveformViewerOperator(bpy.types.Operator, NodeTreeGetter):
    bl_idname = "node.waveform_viewer_callback"
    bl_label = "Waveform Viewer Operator"

    fn_name: bpy.props.StringProperty(default='')

    def execute(self, context):
        node = self.get_node()
        getattr(node, self.fn_name)()
        return {'FINISHED'}


class SvWaveformViewerOperatorDP(bpy.types.Operator, NodeTreeGetter):
    bl_idname = "node.waveform_viewer_dirpick"
    bl_label = "Waveform Viewer Directory Picker"

    filepath: bpy.props.StringProperty(
        name="File Path", description="Filepath used for writing waveform files",
        maxlen=1024, default="", subtype='FILE_PATH')

    def execute(self, context):
        node = self.get_node()
        node.set_dir(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SvWaveformViewer(bpy.types.Node, SverchCustomTreeNode):
    
    """
    Triggers: SvWaveformViewer
    Tooltip: 
    
    A short description for reader of node code
    """


    bl_idname = 'SvWaveformViewer'
    bl_label = 'SvWaveformViewer'
    bl_icon = 'FORCE_HARMONIC'

    n_id: bpy.props.StringProperty(default='')

    def update_socket_count(self, context):
        ... # if self.num_channels < MAX_SOCKETS 

    def get_drawing_attributes(self):
        """
        adjust render location based on preference multiplier setting
        """
        x, y = [int(j) for j in (self.location + Vector((self.width + 20, 0)))[:]]

        try:
            with sv_preferences() as prefs:
                multiplier = prefs.render_location_xy_multiplier
                scale = prefs.render_scale
        except:
            # print('did not find preferences - you need to save user preferences')
            multiplier = 1.0
            scale = 1.0
        x, y = [x * multiplier, y * multiplier]

        return x, y, scale, multiplier


    activate: bpy.props.BoolProperty(name="show graph", update=updateNode)

    num_channels: bpy.props.IntProperty(
        name='num channels', default=1, min=1, max=MAX_SOCKETS,
        description='num channels interleaved', update=updateNode)

    bits: bpy.props.IntProperty(name='bit rate', default=16, min=4, max=192)

    sample_rate: bpy.props.IntProperty(
        name="sample rate", min=8000, default=48000)

    auto_normalize: bpy.props.BoolProperty(
        name="normalize")

    colour_limits: bpy.props.BoolProperty(
        name="color limits")

    multi_channel_sockets: bpy.props.BoolProperty(
        name="multiplex", update=updateNode, description="sockets carry multiple layers of data")

    sample_data_length: bpy.props.IntProperty(min=0, name="sample data len")

    dirname: bpy.props.StringProperty()
    filename: bpy.props.StringProperty()

    def sv_init(self, context):
        self.inputs.new(DATA_SOCKET, 'channel 0')
        self.inputs.new(DATA_SOCKET, 'channel 1')
        self.get_and_set_gl_scale_info()

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
        row = col.row(align=True)
        row.prop(self, 'dirname', text='')
        cb = "node.waveform_viewer_dirpick"
        self.wrapper_tracked_ui_draw_op(row, cb, icon='FILE', text='')
        col.prop(self, "filename")

        if (self.filename and self.dirname):
            col.separator()
            cb = "node.waveform_viewer_callback"
            op = self.wrapper_tracked_ui_draw_op(col, cb, icon='CURSOR', text='WRITE')
            op.fn_name = "process_wave"

        col.separator()
        col.prop(self, 'activate', icon="DESKTOP")
        if self.activate:
            col.label(text="show the oscilloscope")


    def process(self):
        n_id = node_id(self)
        nvBGL.callback_disable(n_id)

        if self.activate:

            x, y, scale, multiplier = self.get_drawing_attributes()
            w = 120.0
            h = 80.0
            grid_data = gridshader(w, h, (x, y))

            config = lambda: None
            config.loc = (x, y)
            config.scale = scale
            config.grid = grid_data

            geom = lambda: None

            draw_data = {
                'mode': 'custom_function',
                'tree_name': self.id_data.name[:],
                'loc': (x, y),
                'custom_function': advanced_grid_xy,
                'args': (geom, config)
            }

            nvBGL.callback_enable(n_id, draw_data)


    def free(self):
        nvBGL.callback_disable(node_id(self))

    def copy(self, node):
        # reset n_id on copy
        self.n_id = ''

    def update(self):
        # handle disconnecting sockets, also disconnect drawing to view?
        if not ("channel 1" in self.inputs):
            return
        try:
            if not self.inputs[0].other or self.inputs[1].other:
                nvBGL.callback_disable(node_id(self))
        except:
            print('Waveform Viewer node update holdout (not a problem)')

    def process_wave(self):
        print('process wave pressed')
        if not self.dirname and self.filename:
            return

        # could be cached. from process()
        wave_data = self.get_wavedata()
        wave_params = self.get_waveparams(wave_data)

        filepath = os.path.join(self.dirname, self.filename)
        filetype = "wav"

        full_filepath_with_ext = f"{filepath}.{filetype}"
        with wave.open(full_filepath_with_ext, 'w') as write_wave:
            write_wave.setparams(wave_params)
            write_wave.writeframesraw(wave_data)

    def get_waveparams(self, wave_data):
        # reference http://blog.acipo.com/wave-generation-in-python/
        # (nchannels, sampwidth, framerate, nframes, comptype, compname)
        
        # sampwidth
        # :    1 = 8bit, 
        # :    2 = 16bit, (int values between +-32767)
        # :    4 = 32bit?
        num_frames = self.num_channels * self.sample_data_length
        return (self.num_channels, int(self.bits / 8), self.sample_rate, num_frames, 'NONE', 'NONE')

    def get_wavedata(self):
        """
        do they match? what convention to use to fill up one if needed..
        - copy opposite channel if channel data is short
        - repeat last channel value until data length matches longest

        yikes, this logic blows...
        """
        if self.multi_channel_sockets:
            data = self.inputs[0].sv_get()
            data = self.interleave(data) if (self.num_channels, len(data)) == (2, 2) else data[0]
        else:
            if self.num_channels == 2:
                data_left = self.inputs[0].sv_get()[0]
                data_right = self.inputs[1].sv_get()[0]
                data = self.interleave([data_left, data_right])
            elif self.num_channels == 1:
                data = self.inputs[0].sv_get()[0]

        # at this point data is a single list.        
        self.sample_data_length = len(data)
        # data = "".join((wave.struct.pack('h', int(d)) for d in data))
        data = b''.join(wave.struct.pack('<h', int(d)) for d in data)
        return data

    def interleave(data_left, data_right):
        # if type data is two numpy arrays:
        # ..
        # else
        flat_list = []
        flat_add = flat_list.extend
        _ = [flat_add((l, r)) for l, r in zip(data_left, data_right)]
        return flat_list

    def set_dir(self, dirname):
        self.dirname = dirname
        print(self.dirname, dirname)


classes = [SvWaveformViewer, SvWaveformViewerOperator, SvWaveformViewerOperatorDP]
register, unregister = bpy.utils.register_classes_factory(classes)