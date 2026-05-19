"""
微信窗口监控模块 - 使用 uiautomation 控制微信 PC 客户端

基于实际 UI 结构（微信 4.x 版本）：
- 微信窗口: WindowControl ClassName='WeChatMainWndForPC' Name='微信'
- 聊天列表: ListControl Name='会话' (左侧面板)
- 消息列表: ListControl Name='消息' (右侧面板，需通过导航获取)
- 输入框: EditControl (右侧面板底部，Name 为联系人名称)
"""

import time
import uiautomation as auto
from typing import Optional, List


# 微信主窗口相关常量
WECHAT_PROCESS_NAME = "WeChat.exe"
WECHAT_MAIN_WINDOW_NAME = "微信"
WECHAT_CLASS_NAME = "WeChatMainWndForPC"


def find_wechat_window() -> Optional[auto.WindowControl]:
    """
    查找微信主窗口

    遍历所有顶层窗口，通过 ClassName 和 Name 匹配微信窗口。

    Returns:
        微信主窗口控件对象，未找到返回 None
    """
    try:
        root = auto.GetRootControl()
        all_windows = root.GetChildren()

        for w in all_windows:
            try:
                if w.ClassName == WECHAT_CLASS_NAME and w.Name == WECHAT_MAIN_WINDOW_NAME:
                    return w
            except Exception:
                continue

        print("[监控] 未找到微信主窗口，请确保微信已登录并打开")
        return None

    except Exception as e:
        print(f"[监控] 查找微信窗口失败: {e}")
        return None


def is_wechat_ready(wechat_window: auto.WindowControl) -> bool:
    """
    检查微信窗口是否可用（已登录且界面加载完成）

    Args:
        wechat_window: 微信主窗口控件

    Returns:
        是否可用
    """
    try:
        return wechat_window.Exists(maxSearchSeconds=0.5)
    except Exception:
        return False


def get_chat_list(wechat_window: auto.WindowControl) -> List[str]:
    """
    获取当前聊天会话列表中的联系人名称

    Args:
        wechat_window: 微信主窗口控件

    Returns:
        联系人名称列表
    """
    try:
        chat_list = wechat_window.ListControl(
            searchDepth=8,
            name="会话"
        )

        if not chat_list.Exists(maxSearchSeconds=0.5):
            print("[监控] 未找到聊天列表控件")
            return []

        items = chat_list.GetChildren()
        names = []
        for item in items:
            try:
                name = item.Name
                if name and name.strip():
                    names.append(name.strip())
            except Exception:
                continue

        return names

    except Exception as e:
        print(f"[监控] 获取聊天列表失败: {e}")
        return []


def find_contact_in_chat_list(
    wechat_window: auto.WindowControl,
    contact_name: str
) -> bool:
    """
    检查指定联系人是否在聊天列表中

    Args:
        wechat_window: 微信主窗口控件
        contact_name: 联系人名称（备注名或昵称）

    Returns:
        是否存在
    """
    try:
        chat_list = wechat_window.ListControl(
            searchDepth=8,
            name="会话"
        )

        if not chat_list.Exists(maxSearchSeconds=0.3):
            return False

        items = chat_list.GetChildren()
        for item in items:
            try:
                if item.Name == contact_name:
                    return True
            except Exception:
                continue

        return False

    except Exception:
        return False


def activate_chat(
    wechat_window: auto.WindowControl,
    contact_name: str
) -> bool:
    """
    激活指定联系人的聊天窗口

    通过聊天列表中的 ListItemControl 找到联系人并点击。

    Args:
        wechat_window: 微信主窗口控件
        contact_name: 联系人名称

    Returns:
        是否成功激活
    """
    try:
        chat_list = wechat_window.ListControl(
            searchDepth=8,
            name="会话"
        )

        if not chat_list.Exists(maxSearchSeconds=0.5):
            print(f"[监控] 未找到聊天列表")
            return False

        items = chat_list.GetChildren()
        for item in items:
            try:
                if item.Name == contact_name:
                    item.Click()
                    time.sleep(0.3)
                    return True
            except Exception:
                continue

        print(f"[监控] 未在聊天列表中找到联系人: {contact_name}")
        return False

    except Exception as e:
        print(f"[监控] 激活聊天窗口失败 ({contact_name}): {e}")
        return False


def _find_control_by_width(control: auto.Control, target_width: int, max_depth: int = 10) -> Optional[auto.Control]:
    """
    递归查找指定宽度的控件

    Args:
        control: 起始控件
        target_width: 目标宽度
        max_depth: 最大递归深度

    Returns:
        找到的控件，未找到返回 None
    """
    try:
        rect = control.BoundingRectangle
        # BoundingRectangle 是 Rect 对象，用 width() 方法获取宽度
        if rect.width() == target_width:
            return control
    except Exception:
        pass

    if max_depth <= 0:
        return None

    try:
        children = control.GetChildren()
        for child in children:
            result = _find_control_by_width(child, target_width, max_depth - 1)
            if result:
                return result
    except Exception:
        pass

    return None


def _navigate_to_right_panel(wechat_window: auto.WindowControl) -> Optional[auto.Control]:
    """
    导航到右侧聊天面板

    通过递归查找宽度为 630px 的 PaneControl 来定位右侧聊天面板，
    兼容不同联系人聊天窗口的 UI 结构差异。

    Returns:
        右侧聊天面板控件，未找到返回 None
    """
    try:
        # 方法1：通过宽度 630px 查找右侧面板（兼容不同结构）
        right_panel = _find_control_by_width(wechat_window, 630, max_depth=15)
        if right_panel:
            return right_panel

        # 方法2：回退到旧的硬编码路径
        children = wechat_window.GetChildren()
        if len(children) > 1:
            main_pane = children[1]
            main_pane_children = main_pane.GetChildren()
            if len(main_pane_children) > 0:
                main_content = main_pane_children[0]
                main_kids = main_content.GetChildren()
                if len(main_kids) > 2:
                    return main_kids[2]

        return None
    except Exception:
        return None


def _find_msg_list(control: auto.Control, max_depth: int = 10) -> Optional[auto.Control]:
    """
    递归查找 ListControl(Name='消息')

    Args:
        control: 起始控件
        max_depth: 最大递归深度

    Returns:
        消息列表控件，未找到返回 None
    """
    try:
        if control.ControlTypeName == "ListControl" and control.Name == "消息":
            return control
    except Exception:
        pass

    if max_depth <= 0:
        return None

    try:
        children = control.GetChildren()
        for child in children:
            result = _find_msg_list(child, max_depth - 1)
            if result:
                return result
    except Exception:
        pass

    return None


def _find_edit_control(control: auto.Control, max_depth: int = 10) -> Optional[auto.Control]:
    """
    递归查找 EditControl（聊天输入框）

    Args:
        control: 起始控件
        max_depth: 最大递归深度

    Returns:
        输入框控件，未找到返回 None
    """
    try:
        if control.ControlTypeName == "EditControl":
            return control
    except Exception:
        pass

    if max_depth <= 0:
        return None

    try:
        children = control.GetChildren()
        for child in children:
            result = _find_edit_control(child, max_depth - 1)
            if result:
                return result
    except Exception:
        pass

    return None


def _navigate_to_msg_input_area(wechat_window: auto.WindowControl) -> Optional[list]:
    """
    导航到消息+输入框区域

    从右侧面板（630px宽）中查找消息列表和输入框区域。
    兼容不同联系人的 UI 结构差异。

    Returns:
        [消息区域控件, 输入框区域控件] 的列表，失败返回 None
    """
    try:
        right_panel = _navigate_to_right_panel(wechat_window)
        if not right_panel:
            return None

        # 在右侧面板中查找消息列表和输入框
        # 消息列表是 ListControl(Name='消息')
        # 输入框是 EditControl

        # 方法1：通过递归查找消息列表和输入框
        msg_list = _find_msg_list(right_panel, max_depth=15)
        edit = _find_edit_control(right_panel, max_depth=15)

        if msg_list and edit:
            # 找到消息列表和输入框后，返回它们所在的区域
            # 消息列表的父控件是消息区域
            # 输入框的父控件是输入框区域
            msg_area = msg_list.GetParentControl()
            edit_area = edit.GetParentControl()
            # 逐级向上找到合适的区域
            return [msg_list, edit]

        # 方法2：回退到通过子控件索引查找
        kids = right_panel.GetChildren()
        if len(kids) < 2:
            return None

        # 尝试 kids[1] 作为消息+输入框区域
        msg_input_area = kids[1]
        area_kids = msg_input_area.GetChildren()
        if len(area_kids) >= 2:
            return [area_kids[0], area_kids[1]]

        return None

        return None

    except Exception:
        return None


def get_last_message_text(wechat_window: auto.WindowControl) -> Optional[str]:
    """
    获取当前聊天窗口中最后一条消息的文本内容

    通过导航到右侧面板的消息列表，获取最后一条消息项的 Name 属性。
    文本消息的 Name 就是消息内容。

    Args:
        wechat_window: 微信主窗口控件

    Returns:
        最后一条消息的文本内容，获取失败返回 None
    """
    try:
        right_panel = _navigate_to_right_panel(wechat_window)
        if not right_panel:
            return None

        # 在右侧面板中递归查找 ListControl(Name='消息')
        msg_list = _find_msg_list(right_panel, max_depth=15)
        if not msg_list:
            return None

        items = msg_list.GetChildren()
        if not items:
            return None

        # 取最后一项（最新消息）
        last_item = items[-1]
        try:
            text = last_item.Name
            if text and text.strip():
                return text.strip()
        except Exception:
            pass

        return None

    except Exception as e:
        print(f"[监控] 获取最后消息失败: {e}")
        return None


def get_chat_input_edit(wechat_window: auto.WindowControl) -> Optional[auto.EditControl]:
    """
    获取当前聊天窗口的输入框控件

    输入框是 EditControl，位于右侧面板底部。
    通过递归查找 EditControl 来定位，兼容不同联系人的 UI 结构差异。

    Args:
        wechat_window: 微信主窗口控件

    Returns:
        输入框控件，未找到返回 None
    """
    try:
        right_panel = _navigate_to_right_panel(wechat_window)
        if not right_panel:
            return None

        # 在右侧面板中递归查找 EditControl
        edit = _find_edit_control(right_panel, max_depth=15)
        if edit:
            return edit

        return None

    except Exception:
        return None


def get_active_chat_name(wechat_window: auto.WindowControl) -> Optional[str]:
    """
    获取当前激活的聊天窗口的联系人名称

    通过查找右侧面板顶部区域的控件来确认当前聊天对象。
    微信 PC 版在右侧面板顶部会显示当前联系人的名称，
    该名称通常出现在 EditControl 的 Name 属性中（输入框的 Name 即为联系人名），
    或者出现在特定的 Text 控件中。

    Args:
        wechat_window: 微信主窗口控件

    Returns:
        当前聊天窗口的联系人名称，获取失败返回 None
    """
    try:
        # 方法1：通过输入框的 Name 属性获取（输入框 Name 通常为联系人名称）
        right_panel = _navigate_to_right_panel(wechat_window)
        if right_panel:
            edit = _find_edit_control(right_panel, max_depth=15)
            if edit and edit.Name and edit.Name.strip():
                return edit.Name.strip()

        # 方法2：直接在微信窗口中查找 EditControl（回退方案）
        edit = wechat_window.EditControl(searchDepth=8)
        if edit.Exists(maxSearchSeconds=0.3):
            name = edit.Name
            if name and name.strip():
                return name.strip()

        return None
    except Exception:
        return None


def bring_window_to_front(wechat_window: auto.WindowControl) -> bool:
    """
    将微信窗口置于前台

    Args:
        wechat_window: 微信主窗口控件

    Returns:
        是否成功
    """
    try:
        if wechat_window.Exists(maxSearchSeconds=0.3):
            wechat_window.SetActive()
            wechat_window.SetTopmost(True)
            time.sleep(0.2)
            wechat_window.SetTopmost(False)
            return True
        return False
    except Exception as e:
        print(f"[监控] 窗口置前失败: {e}")
        return False
