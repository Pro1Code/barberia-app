[app]
title = Barbería App
package.name = barberiaapp
package.domain = org.barberia
version = 1.0.0
source.dir = ./
source.include_exts = py,png,jpg,kv,atlas,ttf
requirements = python3==3.10.9,kivy==2.3.0,plyer,pillow,qrcode
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, INTERNET
android.api = 30
android.minapi = 21
android.ndk = 23b
orientation = portrait
fullscreen = 0
