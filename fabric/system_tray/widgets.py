import gi
from gi.repository import GLib
from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.button import Button
from fabric.system_tray.service import (
    SystemTray as SystemTrayService,
    SystemTrayItem as SystemTrayItemService,
)


watcher: SystemTrayService | None = None


def get_tray_watcher() -> SystemTrayService:
    global watcher
    if not watcher:
        watcher = SystemTrayService()

    return watcher


class SystemTrayItem(Button):
    def __init__(self, item: SystemTrayItemService, icon_size: int, **kwargs):
        super().__init__(**kwargs)
        self._item = item
        self._icon_size = icon_size
        self._image = Image()
        self.set_image(self._image)

        self._item.changed.connect(self.do_update_properties)
        self.connect("button-press-event", self.on_clicked)

        self.do_update_properties()

    def do_update_properties(self, *_):
        pixbuf = self._item.get_preferred_icon_pixbuf(self._icon_size)
        if pixbuf is not None:
            self._image.set_from_pixbuf(pixbuf)
        else:
            self._image.set_from_icon_name("image-missing", self._icon_size)

        tooltip = self._item.tooltip
        self.set_tooltip_markup(
            tooltip.description
            or tooltip.title
            or (self._item.title.title() if self._item.title else None)
            or "Unknown"
        )
        return

    def on_clicked(self, _, event):
        match event.button:
            case 1:  # Left Click
                # 1. Check if the item explicitly says it's a menu
                if self._item.is_menu:
                    self._item.invoke_menu_for_event(event)
                    return

                # 2. Try to activate the item
                try:
                    self._item.activate_for_event(event)
                except GLib.Error:
                    self._item.invoke_menu_for_event(event)
                except Exception as e:
                    # Only log real, unexpected errors
                    logger.warning(
                        f"[SystemTrayItem] Unexpected error activating {self._item.identifier}: {e}"
                    )

            case 2:  # Middle Click
                try:
                    self._item.secondary_activate_for_event(event)
                except GLib.Error:
                    pass  # Secondary activate is often missing, safely ignore

            case 3:  # Right Click
                self._item.invoke_menu_for_event(event)
        return


class SystemTray(Box):
    def __init__(self, icon_size: int = 24, **kwargs):
        super().__init__(**kwargs)
        self._icon_size = icon_size
        self._items: dict[str, SystemTrayItem] = {}

        self._watcher = get_tray_watcher()
        self._watcher.connect("item-added", self.on_item_added)
        self._watcher.connect("item-removed", self.on_item_removed)

    def on_item_added(self, _, item_identifier: str):
        item = self._watcher.items.get(item_identifier)
        if not item:
            return

        item_button = SystemTrayItem(item, self._icon_size)
        self.add(item_button)
        self._items[item.identifier] = item_button
        return

    def on_item_removed(self, _, item_identifier):
        item_button = self._items.get(item_identifier)
        if not item_button:
            return

        self.remove(item_button)
        self._items.pop(item_identifier)
        return


__all__ = ["SystemTray", "SystemTrayItem", "get_tray_watcher"]
