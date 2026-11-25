[app]
presplash.filename = presplash.png
presplash.color = #000000
icon.filename = icon.png
title = Star Fighter
package.name = starfighter
package.domain = org.starfighter
source.dir = .
source.include_exts = py,png
version = 1.0.0
requirements = python3,kivy==2.3.0
orientation = portrait
fullscreen = 1

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
