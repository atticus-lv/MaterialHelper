import bpy
from numpy import mean
from math import sqrt

# 节点偏移距离
C_DIS_X = 80
C_DIS_Y = 40


def connected_socket(self):
    """获取接口所链接的另一非reroute接口

    :param self: bpy.types.NodeSocket
    :return: list[bpy.types.NodeSocket] / None
    """
    _connected_sockets = []

    socket = self
    if socket.is_output:
        # while socket.is_linked and socket.links[0].to_node.bl_rna.name == 'Reroute':
        #     socket = socket.links[0].to_node.outputs[0]
        if socket.is_linked:
            for link in socket.links:
                _connected_sockets.append(link.to_socket)
    else:
        # while socket.is_linked and socket.links[0].from_node.bl_rna.name == 'Reroute':
        #     socket = socket.links[0].from_node.inputs[0]
        if socket.is_linked:
            for link in socket.links:
                _connected_sockets.append(link.from_socket)

    return _connected_sockets if len(_connected_sockets) != 0 else None


def get_dependence(node, selected_nodes=None):
    """获取节点子依赖项

    :param node:  bpy.types.Node
    :param selected_nodes:  list[bpy.types.Node]
    :return: list[bpy.types.Node]
    """
    dependence_nodes = list()
    for input in node.inputs:
        _connected_sockets = connected_socket(input)
        if not _connected_sockets: continue

        for socket in _connected_sockets:
            if (selected_nodes and socket.node in selected_nodes) or (selected_nodes is None):
                dependence_nodes.append(socket.node)

    return dependence_nodes


def get_dependent(node, selected_nodes=None):
    """获取节点父依赖项

    :param node:  bpy.types.Node
    :param selected_nodes:  list[bpy.types.Node]
    :return: list[bpy.types.Node]
    """
    dependent_nodes = list()
    for output in node.outputs:
        _connected_sockets = connected_socket(output)

        if not _connected_sockets: continue

        for socket in _connected_sockets:
            if (selected_nodes and socket.node in selected_nodes) or (selected_nodes is None):
                dependent_nodes.append(socket.node)

    return dependent_nodes


def dpifac():
    """获取用户屏幕缩放，用于矫正节点宽度/长度和摆放位置

    :return: Float
    """
    prefs = bpy.context.preferences.system
    return prefs.dpi * prefs.pixel_size / 72


def get_dimensions(node):
    """获取节点尺寸

    :param node: bpy.types.Node
    :return: (x,y) tuple
    """
    return node.dimensions.x / dpifac(), node.dimensions.y / dpifac()


def get_center_point(node, loc):
    """获取节点中心点，用于评估尺寸和摆放位置

    :param node: bpy.types.Node
    :param loc: (x,y)
    :return: (x,y) tuple
    """

    dim_x, dim_y = get_dimensions(node)
    mid_x = (loc[0] - dim_x) / 2
    mid_y = (loc[1] - dim_y) / 2
    return mid_x, mid_y


def get_offset_from_anim(fac):
    """从动画值获取偏移比例

    :param fac: 动画完成比，0~1
    :return: 偏移比
    """

    return sqrt(min(max(fac, 0), 1))


### TODO 上下对齐（仅限3.2：快捷键新功能）
### TODO 单个节点到多个父级，父级间有依赖关系时候该节点过低的


class MATHP_OT_align_dependence(bpy.types.Operator):
    bl_idname = 'mathp.align_dependence'
    bl_label = 'Align Dependence'

    node_loc_dict = None  # node:{ori_loc:(x,y),tg_loc:(x,y)}

    iteration = 3  # 计算迭代
    # 动画控制
    anim_fac = 0  # 动画比例 0~1
    anim_iter = 30  # 动画更新 秒
    anim_time = 0.05  # 持续时间 秒

    _timer = None

    @classmethod
    def poll(cls, context):
        if not context.window_manager.mathp_node_anim:
            return hasattr(context, 'active_node') and context.active_node

    def append_handle(self):
        self._timer = bpy.context.window_manager.event_timer_add(self.anim_time / self.anim_iter,
                                                                 window=bpy.context.window)  # 添加计时器检测状态
        bpy.context.window_manager.modal_handler_add(self)
        bpy.context.window_manager.mathp_node_anim = True

    def remove_handle(self):
        bpy.context.window_manager.event_timer_remove(self._timer)
        bpy.context.window_manager.mathp_node_anim = False

    def invoke(self, context, event):
        # 初始化
        self.node_loc_dict = dict()
        self._timer = None
        self.anim_fac = 0

        # 获取位置与第一次对齐
        selected_nodes = tuple(context.selected_nodes)
        for i in range(self.iteration):
            # 第二次后 用于检查多个父级依赖的节点
            self.align_dependence(context.active_node, selected_nodes, check_dependent=bool(i == 0))

            self.append_handle()

            return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self.anim_fac >= 1 + 1:  # 添加1动画延迟以完成动画
                self.remove_handle()
                # 强制对齐
                for node, loc_info in self.node_loc_dict.items():
                    node.location = loc_info['tg_loc']

                return {'FINISHED'}
            # 对节点依次进行移动动画
            for i, node in enumerate(self.node_loc_dict.keys()):
                delay = i / len(self.node_loc_dict)
                self.offset_node(node, self.anim_fac, delay)

            self.anim_fac += 1 / (self.anim_iter + 1)  # last delay

        return {"PASS_THROUGH"}

    def offset_node(self, node, anim_fac, delay=0.1):
        """

        :param node: bpy.types.Node
        :param anim_fac: 动画比 0~1
        :param delay: 延迟
        :return:
        """
        ori_loc = self.node_loc_dict[node]['ori_loc']
        tg_loc = self.node_loc_dict[node]['tg_loc']

        offset_fac = get_offset_from_anim(anim_fac - delay)

        offset_x = (tg_loc[0] - ori_loc[0]) * offset_fac
        offset_y = (tg_loc[1] - ori_loc[1]) * offset_fac

        node.location = ori_loc[0] + offset_x, ori_loc[1] + offset_y

    def align_dependence(self, node, selected_nodes=None, check_dependent=False):
        """提取节点的目标位置，用于动画

        :param node: bpy.types.Node
        :param selected_nodes: list[bpy.types.Node]
        :parm check_dependent: 检查父级依赖
        :return: bpy.types.Node
        """

        dependence = get_dependence(node, selected_nodes)

        # 设置初始值
        dim_x, dim_y = get_dimensions(node)

        if node in self.node_loc_dict:
            last_location_x, last_location_y = self.node_loc_dict[node]['tg_loc']
        else:
            last_location_x = node.location.x
            last_location_y = node.location.y
            # active node as dependent
            self.node_loc_dict[node] = {'ori_loc': tuple(node.location),
                                        'tg_loc': tuple(node.location)}

        last_dimensions_x = dim_x
        last_dimensions_y = dim_y

        for i, sub_node in enumerate(dependence):
            # 跳过未选中节点
            if selected_nodes and sub_node not in selected_nodes: continue

            sub_dim_x, sub_dim_y = get_dimensions(sub_node)

            # 对齐父级依赖
            if check_dependent:
                dependent_nodes = get_dependent(sub_node, selected_nodes)
                if len(dependent_nodes) != 1:
                    ori_loc = (sub_node.location.x, sub_node.location.y)

                    dep_loc_x = list()
                    dep_loc_y = list()

                    for i, depend_node in enumerate(dependent_nodes):
                        if depend_node in self.node_loc_dict:
                            dep_loc_x.append(self.node_loc_dict[depend_node]['tg_loc'][0])
                            dep_loc_y.append(self.node_loc_dict[depend_node]['tg_loc'][1])

                        else:
                            dep_loc_x.append(depend_node.location.x)
                            dep_loc_y.append(depend_node.location.y)

                    tg_loc_x = min(dep_loc_x) - sub_dim_x - C_DIS_X
                    tg_loc_y = mean(dep_loc_y)

                    # 记录位置用于动画
                    self.node_loc_dict[sub_node] = {'ori_loc': ori_loc,
                                                    'tg_loc': (tg_loc_x, tg_loc_y)}

                elif len(dependent_nodes) == 1:
                    # 排列同层级自己
                    parent_node = dependent_nodes[0]
                    self.align_dependence(parent_node, selected_nodes)


            # 忽略父级依赖
            else:
                ori_loc = (sub_node.location.x, sub_node.location.y)
                # 目标位置 = 上一个节点位置-当前节点宽度-间隔，y轴向对其第一个节点到依赖节点
                tg_loc_x = last_location_x - sub_dim_x - C_DIS_X
                tg_loc_y = last_location_y - last_dimensions_y - C_DIS_Y if i != 0 else last_location_y
                # 记录位置用于动画
                self.node_loc_dict[sub_node] = {'ori_loc': ori_loc,
                                                'tg_loc': (tg_loc_x, tg_loc_y)}
                # 为下一个节点设置
                last_location_y = tg_loc_y
                last_dimensions_y = sub_dim_y

            self.align_dependence(sub_node, selected_nodes, check_dependent)

        return node


def register():
    bpy.utils.register_class(MATHP_OT_align_dependence)

    # 防止多个操作符同时运行
    bpy.types.WindowManager.mathp_node_anim = bpy.props.BoolProperty(default=False)


def unregister():
    bpy.utils.unregister_class(MATHP_OT_align_dependence)

    del bpy.types.WindowManager.mathp_node_anim
