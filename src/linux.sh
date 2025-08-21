#!/bin/bash
echo "==============================="
echo " KeyCL Setup (Linux)"
echo "==============================="
echo "1. Add to applications menu"
echo "2. Start on startup"
echo "3. Install requirements"
echo "4. Uninstall requirements"
echo "5. Remove from startup"
echo "6. Remove from applications menu"
echo "7. Start script"
echo "8. Install Python"
echo
read -p "Enter your choice [1-8]: " choice

case $choice in
  1)
    echo "[Desktop Entry]
Type=Application
Exec=python3 $(pwd)/main.pyw
Name=KeyCL
Comment=KeyCL App
Icon=utilities-terminal
Terminal=false" > ~/.local/share/applications/keycl.desktop
    echo "Added KeyCL to Applications menu."
    ;;
  2)
    mkdir -p ~/.config/autostart
    cp ~/.local/share/applications/keycl.desktop ~/.config/autostart/
    echo "Added KeyCL to startup."
    ;;
  3)
    echo "Installing requirements..."
    pip3 install customtkinter pygame keyboard pystray Pillow requests
    ;;
  4)
    echo "Uninstalling requirements..."
    pip3 uninstall customtkinter pygame keyboard pystray Pillow requests
    ;;
  5)
    rm -f ~/.config/autostart/keycl.desktop
    echo "Removed KeyCL from startup."
    ;;
  6)
    rm -f ~/.local/share/applications/keycl.desktop
    echo "Removed KeyCL from Applications menu."
    ;;
  7)
    echo "Starting KeyCL..."
    python3 "$(pwd)/main.pyw" &
    ;;
  8)
    echo "Opening Python website..."
    xdg-open "https://www.python.org/downloads/"
    ;;
esac