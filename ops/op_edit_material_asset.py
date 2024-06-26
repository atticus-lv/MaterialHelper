import bpy
import bmesh
import mathutils
from typing import Union
from pathlib import Path

from bpy.types import Operator
from bpy.props import (IntProperty, FloatProperty, StringProperty, EnumProperty, BoolProperty)
from bpy.types import GizmoGroup
from contextlib import contextmanager

from ..prefs.get_pref import get_pref


class State():
    window_count: int = 1
    new_window: Union[bpy.types.Window, None] = None
    last_edit_mat: Union[bpy.types.Material, None] = None


def allowSaveUpdate():
    return bpy.context.window_manager.mathp_global_update is False


@contextmanager
def SaveUpdate():
    bpy.context.window_manager.mathp_global_update = True
    yield
    bpy.context.window_manager.mathp_global_update = False


def tag_redraw():
    '''所有区域重绘制更新'''
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            for region in area.regions:
                region.tag_redraw()


def get_local_selected_assets(context):
    """获取选择的本地资产
    :param context: bpy.context
    :return: 选择项里的本地资产(任何资产类型) bpy.types.Object/Material/World
    """
    cur_lib_name = context.area.spaces.active.params.asset_library_reference
    # print(cur_lib_name)

    match_obj = [asset_file.local_id for asset_file in context.selected_assets if
                 cur_lib_name in {"LOCAL", "ALL"}]

    return match_obj


def split_shader_3d_area():
    """用于切分设置实时预览area

    :return:
    """
    screen = bpy.context.window_manager.windows[-1].screen
    screen.name = 'tmp_mathp'

    screen = bpy.context.window_manager.windows[-1].screen
    screen.name = 'tmp_mathp'

    area_shader = bpy.context.window_manager.windows[-1].screen.areas[0]
    # 拆分 拆分区域大的是原面板
    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.25)
    area_3d = bpy.context.window_manager.windows[-1].screen.areas[-1]
    # 更改窗口类型
    area_shader.type = 'NODE_EDITOR'
    area_shader.ui_type = 'ShaderNodeTree'

    # 窗口设置
    area_3d.type = 'VIEW_3D'
    space = area_3d.spaces[0]
    space.overlay.show_overlays = False
    space.show_gizmo = False
    space.region_3d.view_perspective = 'PERSP'

    shading_type = get_pref().shading_type

    space.shading.type = shading_type
    space.lock_object = bpy.context.object  # 锁定物体
    space.shading.use_scene_world_render = False
    space.shading.use_scene_lights_render = False
    space.shading.studio_light = 'city.exr'

    # set view
    space.region_3d.view_rotation = (0.62, 0.38, 0.35, 0.58)
    space.region_3d.view_location = (0.16, 0, 0.16)

    # solo
    override = {'area': area_3d}
    try:
        with bpy.context.temp_override(**override):
            bpy.ops.view3d.localview('INVOKE_DEFAULT')
    except RuntimeError:
        if 'tmp_mathp' in bpy.data.screens:
            # 清理多余screen
            for s in bpy.data.screens:
                if not s.name.startswith('tmp_mathp'): continue
                # 清除屏幕
                s.user_clear()
                # 清除局部视图
                for area in s.areas:
                    if area.type != 'VIEW_3D': continue
                    for region in area.regions:
                        if region.type != 'WINDOW': continue

                        override2 = {'area': area, 'region': region}  # override context
                        try:
                            with bpy.context.temp_override(**override2):
                                bpy.ops.view3d.view_selected(use_all_regions=False)
                        except:
                            pass
                        break

    # header
    space.show_region_header = False
    space.shading.studio_light = 'forest.exr'

    return area_shader, area_3d


def update_window_count():
    State.window_count = len(bpy.context.window_manager.windows)
    State.new_window = bpy.context.window_manager.windows[-1]


def window_style_1():
    """大窗口,左属性面板右节点面板

    :return:
    """
    update_window_count()
    bpy.ops.wm.window_new()  # 使用新窗口
    update_window_count()
    split_shader_3d_area()


def window_style_2(flip_header=True):
    """小面板

    :return:
    """
    # 创建新窗口
    # bpy.ops.render.view_show('INVOKE_AREA')
    update_window_count()
    bpy.ops.screen.userpref_show("INVOKE_AREA")  # 使用偏好设置而不是渲染（版本更改导致渲染不再置顶）
    update_window_count()

    if get_pref().use_shader_ball_pv:
        area_3d, area_shader = split_shader_3d_area()
    else:
        screen = bpy.context.window_manager.windows[-1].screen
        screen.name = 'tmp_mathp'

        area_shader = screen.areas[0]
        area_shader.type = 'NODE_EDITOR'
        area_shader.ui_type = 'ShaderNodeTree'

    # 侧边栏
    bpy.context.space_data.show_region_ui = True if get_pref().show_UI else False
    # 翻转菜单栏
    for region in area_shader.regions:
        override = {'area': area_shader, 'region': region}
        if region == 'UI':
            if get_pref().UI_direction == 'LEFT':
                bpy.ops.screen.region_flip(override, 'INVOKE_DEFAULT')
        elif region == 'UI' and flip_header:
            bpy.ops.screen.region_flip(override, 'INVOKE_DEFAULT')

            # 3.2
            # with bpy.context.temp_override(**override):
            #     if flip_header: bpy.ops.screen.region_flip('INVOKE_DEFAULT')

        # 等待blender修复
        # if region.type == 'WINDOW':
        #     with bpy.context.temp_override(area=area, region=region):
        #         bpy.ops.node.view_all("INVOKE_AREA")


def pop_up_window(style='2'):
    """

    :return:
    """
    if style == '1':
        window_style_1()
    else:
        window_style_2()


def set_shader_ball_mat(mat, coll):
    """导入并设置材质球模型/材质

    :param mat: bpy.types.Material
    :param coll: bpy.types.Collection
    :return:
    """
    # 获取设置
    with SaveUpdate():
        mat_pv_type = get_pref().shader_ball
        if mat_pv_type == 'NONE':
            mat_pv_type = mat.mathp_preview_render_type

        shader_ball_lib = Path(__file__).parent.parent.joinpath('shader_ball_lib')
        blend_file = shader_ball_lib.joinpath('shader_ball.blend')

        with bpy.data.libraries.load(str(blend_file), link=False) as (data_from, data_to):
            data_to.objects = [mat_pv_type]

        tmp_obj = data_to.objects[0]

        # 移动到比较远的地方
        tmp_obj.location = (10000, 10000, 10000)

        coll.objects.link(tmp_obj)

        # 设置激活项和材质
        bpy.context.view_layer.objects.active = tmp_obj

        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.object.select_set(True)
        bpy.ops.object.shade_smooth()

        tmp_obj.select_set(True)
        tmp_obj.active_material = mat

        State.last_edit_mat = mat.name


class MATHP_OT_edit_material_asset(Operator):
    bl_idname = 'mathp.edit_material_asset'
    bl_label = 'Edit Material Asset'

    material: StringProperty(name='Material Name', options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return (hasattr(context, 'selected_assets') and context.selected_assets) or context.asset

    def _return(self, msg, type='INFO'):
        """
        :param msg: 报告给用户的信息
        :param type: 信息/警告/错误弹窗
        :return: {'CANCELLED'}/{'FINISHED'}
        """

        self.report({type}, msg)
        if type == 'INFO':
            return {"FINISHED"}
        else:
            return {"CANCELLED"}

    def get_data(self, data_lib, name):
        """

        :param data_lib: 数据类型 str
        :param name: 数据名字
        :return:
        """
        data_lib = getattr(bpy.data, data_lib)
        data = data_lib.get(name)
        if not data:
            data_lib.new(name=name)

        return data

    def execute(self, context):
        if self.material:
            selected_mat = [bpy.data.materials[self.material], ]
        else:
            match_obj = get_local_selected_assets(context)
            selected_mat = [obj for obj in match_obj if isinstance(obj, bpy.types.Material)]

            if not selected_mat:
                return self._return(msg='请选择一个本地材质资产', type='WARNING')
            # print(selected_mat)

        # 创建集合
        tmp_coll = bpy.data.collections[
            'tmp_mathp'] if 'tmp_mathp' in bpy.data.collections else bpy.data.collections.new(
            'tmp_mathp')
        if 'tmp_mathp' not in context.scene.collection.children:
            context.scene.collection.children.link(tmp_coll)

        # 设置材质球/材质

        set_shader_ball_mat(selected_mat[0], tmp_coll)
        selected_mat[0].asset_generate_preview()

        # 设置鼠标位置，以便弹窗出现在正中央
        w = context.window
        w_center_x, w_center_y = w.width / 2, w.height / 2
        w.cursor_warp(int(w_center_x), int(w_center_y))
        # 弹窗
        pop_up_window(style=get_pref().window_style)

        return {'FINISHED'}


class MATHP_OT_update_mat_pv(Operator):
    """Update Material Asset Preview"""
    bl_idname = 'mathp.update_mat_pv'
    bl_label = 'Update Material Preview'

    mat_name: StringProperty(name='Material Name')

    def execute(self, context):
        # 更新材质预览
        mat = bpy.data.materials.get(self.mat_name)
        if mat:
            mat.asset_generate_preview()

        return {'FINISHED'}


class MATHP_UI_update_mat_pv(GizmoGroup):
    """use_tooltip"""
    bl_idname = "MATHP_UI_update_mat_pv"
    bl_label = "Update Material Preview"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        if context.area.type == 'NODE_EDITOR' and context.area.ui_type == 'ShaderNodeTree':
            return hasattr(context, 'material') and context.material.asset_data is not None

    def draw_prepare(self, context):
        region = context.region

        self.foo_gizmo.matrix_basis[0][3] = region.width - 40
        self.foo_gizmo.matrix_basis[1][3] = 40
        self.foo_gizmo.scale_basis = (80 * 0.35) / 2

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_button_2d")
        gz.icon = 'FILE_REFRESH'
        gz.draw_options = {'BACKDROP', 'OUTLINE'}
        gz.use_tooltip = True
        gz.alpha = 0
        gz.color_highlight = 0.8, 0.8, 0.8
        gz.alpha_highlight = 0.2

        gz.scale_basis = (80 * 0.35) / 2  # Same as buttons defined in C

        props = gz.target_set_operator("mathp.update_mat_pv")
        props.mat_name = context.material.name

        self.foo_gizmo = gz


from bpy.app.handlers import persistent


@persistent
def del_tmp_obj(scene, depsgraph):
    """删除用于预览的模型/网格/屏幕缓存

    :param scene:
    :param depsgraph:
    :return:
    """
    try:
        _ = bpy.context.window_manager.windows[State.window_count - 1]
        return
    except IndexError:
        pass
    finally:
        update_window_count()

    if allowSaveUpdate():
        if mat := bpy.data.materials.get(State.last_edit_mat):
            mat.asset_generate_preview()

        coll = bpy.data.collections.get('tmp_mathp')
        if coll:
            # 清理临时物体
            for obj in bpy.data.collections['tmp_mathp'].objects:
                me = obj.data
                bpy.data.objects.remove(obj)
                bpy.data.meshes.remove(me)

            bpy.data.collections.remove(coll)

        if 'tmp_mathp' in bpy.data.screens:
            # 清理多余screen
            for s in bpy.data.screens:
                if not s.name.startswith('tmp_mathp'): continue
                s.user_clear()


def update_shader_ball(self, context):
    coll = bpy.data.collections.get('tmp_mathp')

    if not coll: return

    mat = self.id_data

    for obj in bpy.data.collections['tmp_mathp'].objects:
        me = obj.data
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(me)

    set_shader_ball_mat(mat, coll)
    mat.asset_generate_preview()

    for a in context.window.screen.areas:
        if a.type == 'VIEW_3D':
            a.spaces[0].lock_object = bpy.context.object


def register():
    bpy.types.WindowManager.mathp_global_update = BoolProperty(name='Update', default=False)
    bpy.types.Material.mathp_preview_render_type = EnumProperty(name='Shader Ball',
                                                                items=[
                                                                    ('FLAT', 'Flat', '', 'MATPLANE', 0),
                                                                    ('SPHERE', 'Sphere', '', 'MATSPHERE', 1),
                                                                    ('CUBE', 'Cube', '', 'MATCUBE', 2),
                                                                    ('HAIR', 'Hair', '', 'CURVES', 3),
                                                                    ('SHADERBALL', 'Shader Ball', '', 'MATSHADERBALL',
                                                                     4),
                                                                    ('CLOTH', 'Cloth', '', 'MATCLOTH', 5),
                                                                    ('FLUID', 'Fluid', '', 'MATFLUID', 6),
                                                                ], default='SPHERE', update=update_shader_ball)
    if not MATHP_OT_edit_material_asset.is_registered:
        bpy.utils.register_class(MATHP_OT_edit_material_asset)
    bpy.utils.register_class(MATHP_OT_update_mat_pv)
    # bpy.utils.register_class(MATHP_UI_update_mat_pv)
    bpy.app.handlers.depsgraph_update_pre.append(del_tmp_obj)


def unregister():
    bpy.app.handlers.depsgraph_update_pre.remove(del_tmp_obj)
    bpy.utils.unregister_class(MATHP_OT_edit_material_asset)
    bpy.utils.unregister_class(MATHP_OT_update_mat_pv)
    # bpy.utils.unregister_class(MATHP_UI_update_mat_pv)

    del bpy.types.Material.mathp_preview_render_type
