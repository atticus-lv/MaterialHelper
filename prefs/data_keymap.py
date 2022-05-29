import bpy

addon_keymaps = []


def register():
    wm = bpy.context.window_manager
    if not wm.keyconfigs.addon: return
    # 双击点开材质
    km = wm.keyconfigs.addon.keymaps.new(name='File Browser', space_type='FILE_BROWSER')
    kmi = km.keymap_items.new("mathp.edit_material_asset", 'LEFTMOUSE', 'DOUBLE_CLICK', ctrl=False, shift=False)
    addon_keymaps.append((km, kmi))
    # 删除材质菜单
    km = wm.keyconfigs.addon.keymaps.new(name='File Browser', space_type='FILE_BROWSER')
    kmi = km.keymap_items.new("wm.call_menu", 'X', 'PRESS', ctrl=False, shift=False)
    kmi.properties.name = 'MATHP_MT_asset_delete_meun'
    addon_keymaps.append((km, kmi))
    # 节点对齐
    km = wm.keyconfigs.addon.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new('mathp.align_dependence', 'A', 'PRESS', ctrl=True)
    addon_keymaps.append((km, kmi))
    # 控制依赖项
    km = wm.keyconfigs.addon.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new('mathp.move_dependence', 'D', 'PRESS')
    addon_keymaps.append((km, kmi))


def unregister():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc: return

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()
