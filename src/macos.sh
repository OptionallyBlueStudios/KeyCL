#!/bin/bash
echo "==============================="
echo " KeyCL Setup (macOS)"
echo "==============================="
echo "1. Add to Applications (Automator)"
echo "2. Start on startup"
echo "3. Install requirements"
echo "4. Uninstall requirements"
echo "5. Remove from startup"
echo "6. Remove from Applications"
echo "7. Start script"
echo "8. Install Python"
echo
read -p "Enter your choice [1-8]: " choice

case $choice in
  1)
    mkdir -p ~/Applications
    echo "#!/bin/bash
python3 $(pwd)/main.pyw" > ~/Applications/KeyCL.command
    chmod +x ~/Applications/KeyCL.command
    echo "Added KeyCL to Applications."
    ;;
  2)
    mkdir -p ~/Library/LaunchAgents
    cat <<EOF > ~/Library/LaunchAgents/com.keycl.autostart.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" \
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.keycl.autostart</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$(pwd)/main.pyw</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF
    launchctl load ~/Library/LaunchAgents/com.keycl.autostart.plist
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
    launchctl unload ~/Library/LaunchAgents/com.keycl.autostart.plist
    rm -f ~/Library/LaunchAgents/com.keycl.autostart.plist
    echo "Removed KeyCL from startup."
    ;;
  6)
    rm -f ~/Applications/KeyCL.command
    echo "Removed KeyCL from Applications."
    ;;
  7)
    echo "Starting KeyCL..."
    python3 "$(pwd)/main.pyw" &
    ;;
  8)
    echo "Opening Python website..."
    open "https://www.python.org/downloads/"
    ;;
esac
