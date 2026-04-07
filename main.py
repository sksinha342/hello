"""
Kivy Image Perspective Crop App
================================
Tap 4 corners on a loaded image to define the perspective quad,
then press "Crop" to get the rectified (bird's-eye) view.
"""

import os
import time
import numpy as np

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image as KvImage
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, Ellipse, Line
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.utils import platform

import cv2


# ── helpers ──────────────────────────────────────────────────────────────────

def order_points(pts):
    """Return points in order: top-left, top-right, bottom-right, bottom-left."""
    pts = np.array(pts, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left  (smallest sum)
    rect[2] = pts[np.argmax(s)]   # bottom-right (largest sum)

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right  (smallest diff)
    rect[3] = pts[np.argmax(diff)]  # bottom-left (largest diff)

    return rect


def four_point_transform(image, pts):
    """Apply perspective transform to *image* using 4 corner *pts*."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1],
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_width, max_height))
    return warped


def bgr_to_texture(bgr_img):
    """Convert a BGR numpy array to a Kivy Texture."""
    rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    flipped = cv2.flip(rgb, 0)          # Kivy textures are bottom-up
    h, w, _ = flipped.shape
    tex = Texture.create(size=(w, h), colorfmt="rgb")
    tex.blit_buffer(flipped.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
    return tex


# ── widgets ──────────────────────────────────────────────────────────────────

class ImageCanvas(FloatLayout):
    """FloatLayout that shows an image and collects up to 4 tap points."""

    MAX_POINTS = 4
    MARKER_R = 10  # dot radius in screen px

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kv_image = KvImage(allow_stretch=True, keep_ratio=True,
                                size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.add_widget(self.kv_image)

        self.cv_image = None          # original BGR numpy array
        self.screen_points = []       # tapped positions in widget coords
        self._dot_instructions = []   # canvas instructions to remove on reset

    # ── public API ────────────────────────────────────────────────────────

    def load_image(self, path):
        self.cv_image = cv2.imread(path)
        if self.cv_image is None:
            return False
        self.kv_image.texture = bgr_to_texture(self.cv_image)
        self.reset_points()
        return True

    def reset_points(self):
        for instr in self._dot_instructions:
            self.canvas.remove(instr)
        self._dot_instructions.clear()
        self.screen_points.clear()

    def get_image_points(self):
        """Map screen tap coords to original image pixel coords."""
        if self.cv_image is None or len(self.screen_points) != self.MAX_POINTS:
            return None

        ih, iw = self.cv_image.shape[:2]
        tex = self.kv_image.texture
        if tex is None:
            return None

        # Size of the displayed image region (respecting keep_ratio)
        widget_w, widget_h = self.kv_image.size
        scale = min(widget_w / iw, widget_h / ih)
        disp_w = iw * scale
        disp_h = ih * scale

        # Top-left corner of the image within the widget
        offset_x = self.kv_image.x + (widget_w - disp_w) / 2
        offset_y = self.kv_image.y + (widget_h - disp_h) / 2

        img_pts = []
        for (sx, sy) in self.screen_points:
            ix = (sx - offset_x) / scale
            # Kivy Y is bottom-up; image Y is top-down
            iy = ih - (sy - offset_y) / scale
            img_pts.append((ix, iy))
        return img_pts

    # ── touch handling ────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if self.cv_image is None:
            return True
        if len(self.screen_points) >= self.MAX_POINTS:
            return True

        self.screen_points.append(touch.pos)
        self._draw_marker(touch.pos)
        return True

    def _draw_marker(self, pos):
        r = self.MARKER_R
        x, y = pos[0] - r, pos[1] - r
        with self.canvas:
            c = Color(1, 0, 0, 1)
            e = Ellipse(pos=(x, y), size=(r * 2, r * 2))
        self._dot_instructions.extend([c, e])

        # Draw lines connecting dots when we have 2+
        if len(self.screen_points) >= 2:
            flat = [coord for pt in self.screen_points for coord in pt]
            if len(self.screen_points) == self.MAX_POINTS:
                flat += list(self.screen_points[0])   # close quad
            with self.canvas:
                lc = Color(0, 1, 0, 1)
                ln = Line(points=flat, width=2)
            self._dot_instructions.extend([lc, ln])


# ── main layout ──────────────────────────────────────────────────────────────

class PerspectiveCropLayout(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        # ── toolbar ──
        toolbar = BoxLayout(size_hint=(1, None), height=56, spacing=6,
                            padding=[6, 4, 6, 4])

        self.btn_open = Button(text="Open Image", size_hint=(0.3, 1))
        self.btn_open.bind(on_release=self._open_chooser)

        self.btn_crop = Button(text="Crop", size_hint=(0.2, 1),
                               disabled=True)
        self.btn_crop.bind(on_release=self._do_crop)

        self.btn_reset = Button(text="Reset Points", size_hint=(0.25, 1),
                                disabled=True)
        self.btn_reset.bind(on_release=self._reset)

        self.btn_save = Button(text="Save", size_hint=(0.25, 1),
                               disabled=True)
        self.btn_save.bind(on_release=self._save_result)

        toolbar.add_widget(self.btn_open)
        toolbar.add_widget(self.btn_crop)
        toolbar.add_widget(self.btn_reset)
        toolbar.add_widget(self.btn_save)
        self.add_widget(toolbar)

        # ── status label ──
        self.lbl_status = Label(
            text="Open an image, then tap 4 corners to define the crop area.",
            size_hint=(1, None), height=34, font_size="13sp",
            halign="center", valign="middle"
        )
        self.lbl_status.bind(size=self.lbl_status.setter("text_size"))
        self.add_widget(self.lbl_status)

        # ── canvas ──
        self.canvas_widget = ImageCanvas(size_hint=(1, 1))
        self.add_widget(self.canvas_widget)

        self.result_image = None      # BGR numpy array of cropped result
        self._chooser_popup = None

    # ── file chooser ─────────────────────────────────────────────────────

    def _open_chooser(self, *_):
        if platform == "android":
            start_path = "/sdcard"
        else:
            start_path = os.path.expanduser("~")

        fc = FileChooserListView(
            path=start_path,
            filters=["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"],
            size_hint=(1, 1),
        )
        content = BoxLayout(orientation="vertical")
        content.add_widget(fc)

        btn_bar = BoxLayout(size_hint=(1, None), height=48, spacing=6,
                            padding=[6, 4, 6, 4])
        btn_select = Button(text="Select")
        btn_cancel = Button(text="Cancel")
        btn_bar.add_widget(btn_select)
        btn_bar.add_widget(btn_cancel)
        content.add_widget(btn_bar)

        popup = Popup(title="Choose Image", content=content,
                      size_hint=(0.95, 0.9))
        btn_select.bind(on_release=lambda *_: self._on_file_select(fc.selection, popup))
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()
        self._chooser_popup = popup

    def _on_file_select(self, selection, popup):
        popup.dismiss()
        if not selection:
            return
        path = selection[0]
        if self.canvas_widget.load_image(path):
            self.result_image = None
            self.btn_crop.disabled = False
            self.btn_reset.disabled = False
            self.btn_save.disabled = True
            self.lbl_status.text = (
                "Image loaded. Tap 4 corners (in any order) then press Crop."
            )
        else:
            self.lbl_status.text = f"Could not load: {os.path.basename(path)}"

    # ── crop ─────────────────────────────────────────────────────────────

    def _do_crop(self, *_):
        pts = self.canvas_widget.get_image_points()
        if pts is None:
            n = len(self.canvas_widget.screen_points)
            self.lbl_status.text = (
                f"Need 4 corner taps — you have {n} so far. Keep tapping!"
            )
            return

        try:
            warped = four_point_transform(self.canvas_widget.cv_image, pts)
        except Exception as exc:
            self.lbl_status.text = f"Crop failed: {exc}"
            return

        self.result_image = warped
        self.canvas_widget.kv_image.texture = bgr_to_texture(warped)
        self.canvas_widget.reset_points()
        self.btn_save.disabled = False
        self.lbl_status.text = "Crop done! Press Save to export, or open another image."

    # ── reset ─────────────────────────────────────────────────────────────

    def _reset(self, *_):
        self.canvas_widget.reset_points()
        # Restore original image display if we still have it
        if self.canvas_widget.cv_image is not None:
            self.canvas_widget.kv_image.texture = bgr_to_texture(
                self.canvas_widget.cv_image
            )
        self.result_image = None
        self.btn_save.disabled = True
        self.lbl_status.text = "Points reset. Tap 4 corners again."

    # ── save ──────────────────────────────────────────────────────────────

    def _save_result(self, *_):
        if self.result_image is None:
            return

        if platform == "android":
            out_dir = "/sdcard/Pictures"
        else:
            out_dir = os.path.expanduser("~")

        os.makedirs(out_dir, exist_ok=True)
        filename = f"crop_{int(time.time())}.jpg"
        out_path = os.path.join(out_dir, filename)

        cv2.imwrite(out_path, self.result_image)
        self.lbl_status.text = f"Saved: {out_path}"


# ── app ──────────────────────────────────────────────────────────────────────

class PerspectiveCropApp(App):
    title = "Perspective Crop"

    def build(self):
        Window.clearcolor = (0.12, 0.12, 0.12, 1)
        return PerspectiveCropLayout()


if __name__ == "__main__":
    PerspectiveCropApp().run()
