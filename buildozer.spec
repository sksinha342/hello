[app]

# App title & package
title = Perspective Crop
package.name = perspectivecrop
package.domain = org.sksinha342

# Entry point
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0.0

# Dependencies (pip packages bundled into the APK)
requirements = python3,kivy==2.2.1,opencv,numpy,android

# Android orientation
orientation = portrait

# Android permissions
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,CAMERA

android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True

# Presplash / icon (place your own 512×512 icon.png in the project root)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

[buildozer]

# Log level: 0 = error, 1 = info, 2 = debug
log_level = 2

warn_on_root = 1
