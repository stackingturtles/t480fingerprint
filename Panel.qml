// Copyright (c) 2026 Stacking Turtles Ltd. SPDX-License-Identifier: MIT
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons

Item {
    id: root
    property var shell: null
    property var manifest: null
    property bool opened: false
    property var device: ({})
    readonly property var fonts: Style.font
    property string statusError: ""
    readonly property string bridge: decodeURIComponent(Qt.resolvedUrl("scripts/plugin.py").toString().replace(/^file:\/\//, ""))

    function open() {
        opened = true
        refresh()
        Qt.callLater(function() { card.forceActiveFocus() })
    }
    function close() { opened = false }
    function dismiss() {
        if (root.shell) root.shell.hide("io.github.stackingturtles.t480fingerprint")
        else close()
    }
    function refresh() {
        if (!statusProcess.running) statusProcess.running = true
    }
    function launch(action) {
        Quickshell.execDetached(["omarchy-launch-terminal", "/usr/bin/python3", "-I", root.bridge, action, finger.currentValue])
        dismiss()
    }

    Process {
        id: statusProcess
        command: ["/usr/bin/python3", "-I", root.bridge, "status"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text)
                    root.device = result
                    root.statusError = result.error || ""
                } catch (error) {
                    root.device = ({})
                    root.statusError = "Could not read fingerprint status."
                }
            }
        }
        onExited: function(exitCode) {
            if (exitCode !== 0) root.statusError = "Could not read fingerprint status."
        }
    }
    Timer {
        interval: 5000
        repeat: true
        running: root.opened
        onTriggered: root.refresh()
    }

    PanelWindow {
        visible: root.opened
        anchors { top: true; bottom: true; left: true; right: true }
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "t480fingerprint"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

        Rectangle {
            anchors.fill: parent
            color: "#99000000"
            MouseArea { anchors.fill: parent; onClicked: root.dismiss() }
        }
        Rectangle {
            id: card
            anchors.centerIn: parent
            width: Style.space(540)
            height: content.implicitHeight + Style.space(48)
            scale: Math.min(1, (parent.width - 32) / width, (parent.height - 32) / height)
            color: Color.background
            border.color: Color.foreground
            border.width: 1
            radius: Style.space(12)
            focus: true
            Keys.onEscapePressed: root.dismiss()
            MouseArea { anchors.fill: parent }

            ColumnLayout {
                id: content
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: Style.space(24) }
                spacing: Style.space(12)

                Text {
                    text: "T480 Fingerprint"
                    color: Color.foreground
                    font.family: root.fonts.family
                    font.pixelSize: root.fonts.title
                    font.bold: true
                }
                Text {
                    Layout.fillWidth: true
                    text: "Prepare your fingerprint, then enable it for sudo."
                    color: Color.foreground
                    font.family: root.fonts.family
                    wrapMode: Text.WordWrap
                }
                Text {
                    Layout.fillWidth: true
                    text: root.statusError ||
                        ("Reader: " + (root.device.reader ? "detected" : "not detected") + "\n" +
                         "Package: " + (root.device.version || "not installed") + "\n" +
                         "Sudo: " + (root.device.sudoEnabled ? "fingerprint enabled" : "password only"))
                    color: Color.foreground
                    font.family: root.fonts.family
                    wrapMode: Text.WordWrap
                    lineHeight: 1.4
                }
                Controls.ComboBox {
                    id: finger
                    Layout.fillWidth: true
                    textRole: "label"
                    valueRole: "value"
                    model: [
                        {label: "Right index finger", value: "right-index-finger"},
                        {label: "Left index finger", value: "left-index-finger"},
                        {label: "Right thumb", value: "right-thumb"},
                        {label: "Left thumb", value: "left-thumb"},
                        {label: "Right middle finger", value: "right-middle-finger"},
                        {label: "Left middle finger", value: "left-middle-finger"},
                        {label: "Right ring finger", value: "right-ring-finger"},
                        {label: "Left ring finger", value: "left-ring-finger"},
                        {label: "Right little finger", value: "right-little-finger"},
                        {label: "Left little finger", value: "left-little-finger"}
                    ]
                    Accessible.name: "Finger to enroll or verify"
                }
                GridLayout {
                    columns: 2
                    Layout.fillWidth: true
                    Controls.Button {
                        Layout.fillWidth: true
                        text: root.device.ready ? "Reinstall driver" : "Install / update driver"
                        onClicked: root.launch("install")
                    }
                    Controls.Button {
                        Layout.fillWidth: true
                        text: "Prepare fingerprint"
                        enabled: root.device.reader === true && root.device.ready === true
                        onClicked: root.launch("prepare")
                    }
                    Controls.Button {
                        Layout.fillWidth: true
                        text: "Test fingerprint"
                        enabled: root.device.reader === true && root.device.ready === true
                        onClicked: root.launch("verify")
                    }
                    Controls.Button {
                        Layout.fillWidth: true
                        text: "Enable fingerprint sudo"
                        enabled: root.device.reader === true && root.device.ready === true
                        onClicked: root.launch("enable")
                    }
                    Controls.Button {
                        Layout.fillWidth: true
                        text: "Restore password-only sudo"
                        enabled: !!root.device.version
                        onClicked: root.launch("disable")
                    }
                    Controls.Button {
                        Layout.fillWidth: true
                        text: "Close"
                        onClicked: root.dismiss()
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: "Actions open in a terminal. Installation and setup may ask for your password. A failed sudo scan falls back to your password."
                    color: Color.foreground
                    font.family: root.fonts.family
                    font.pixelSize: root.fonts.caption
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
