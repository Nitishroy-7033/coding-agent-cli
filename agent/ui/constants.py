ASCII_LOGO = r"""
 [white]█▀█ █▀█ █▀▀ █▀█ █▀▀ █▀█ █▀▄ █▀▀[/white]
 [dim]█▄█ █▀▀ █▀▀ █ █ █▄▄ █▄█ █▄▀ █▄▄[/dim]
"""

CSS = """
    Screen {
        background: #0a0a0a;
        color: #c9d1d9;
        align: center middle;
        layers: base popup;
    }

    * {
        scrollbar-size: 1 1;
    }
    
    #mention-popup {
        display: none;
        layer: popup;
        width: 40;
        height: 10;
        background: #161b22;
        border: solid #30363d;
        dock: bottom;
        margin-bottom: 5;
        margin-left: 2;
    }
    
    Scrollbar {
        background: transparent;
    }
    
    Scrollbar > .scrollbar-slider {
        background: #21262d;
    }
    
    Scrollbar > .scrollbar-slider:hover {
        background: #30363d;
    }

    Screen.chat-mode {
        align: left top;
    }

    #app-container {
        width: 100%;
        max-width: 90;
        height: auto;
        align: center middle;
        layout: horizontal;
    }

    Screen.chat-mode #app-container {
        max-width: 100%;
        height: 100%;
        align: left top;
    }

    #main-column {
        width: 1fr;
        height: auto;
        align: center middle;
    }

    Screen.chat-mode #main-column {
        width: 3fr;
        height: 100%;
        align: left top;
        padding-right: 2;
    }

    #sidebar {
        display: none;
        width: 1fr;
        max-width: 40;
        height: 100%;
        background: #0f1115;
        padding: 1 2;
        border-left: solid #21262d;
    }

    Screen.chat-mode #sidebar {
        display: block;
    }

    #logo-container {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-align: center;
        margin-bottom: 2;
    }
    
    Screen.chat-mode #logo-container {
        display: none;
    }

    #logo {
        text-align: center;
        width: 100%;
    }

    #chat-container {
        width: 100%;
        height: auto;
        max-height: 50vh;
        background: transparent;
        padding: 1 0;
        margin-bottom: 1;
        display: none;
    }

    Screen.chat-mode #chat-container {
        display: block;
        height: 1fr;
        max-height: 100%;
    }

    .user-msg {
        border-left: solid #58a6ff;
        padding: 0 1;
        margin: 1 0;
        color: #f0f6fc;
    }

    .agent-msg-header {
        padding: 0 1;
        margin-top: 1;
        color: #8b949e;
    }

    .agent-msg {
        padding: 0 1;
        margin: 0 0 1 0;
        color: #c9d1d9;
    }

    .tool-msg {
        border-left: solid #d29922;
        padding: 0 1;
        margin: 1 0;
        color: #8b949e;
    }

    #input-card {
        width: 100%;
        height: auto;
        background: #1a1b20;
        padding:1  1 1 1;
    }
    
    Screen.chat-mode #input-card {
        border-left: solid #58a6ff;
    }

    #prompt-input {
        background: #1a1b20;
        border: none;
        color: #f0f6fc;
        padding: 0 0;
    }

    #status-line {
        margin-top: 0;
        content-align: left middle;
    }
    
    Screen.chat-mode #status-line {
        display: none;
    }

    #shortcuts-line {
        color: #8b949e;
        content-align: left middle;
        margin-bottom: 2;
        padding-left: 2;
    }
    
    Screen.chat-mode #shortcuts-line {
        display: none;
    }

    #tip-line {
        color: #8b949e;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    Screen.chat-mode #tip-line {
        display: none;
    }

    #footer-bar {
        display: none;
    }
    
    .sb-section {
        margin-bottom: 1;
    }
    
    .sb-title {
        color: #f0f6fc;
        text-style: bold;
        margin-top: 1;
    }
    
    .sb-content {
        color: #8b949e;
        margin-bottom: 1;
    }
    
    #sb-tree {
        height: 1fr;
        border: none;
        background: transparent;
        padding-top: 1;
    }
    
    #sb-footer {
        dock: bottom;
        height: 2;
    }
    
    #input-footer {
        display: none;
        width: 100%;
        height: auto;
        layout: horizontal;
        color: #8b949e;
    }
    
    Screen.chat-mode #input-footer {
        display: block;
    }
    
    #input-footer-left {
        width: 1fr;
        height: auto;
        content-align: left middle;
    }
    
    #input-footer-right {
        width: auto;
        height: auto;
        content-align: right middle;
    }
"""
