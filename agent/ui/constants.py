# ── Catppuccin Mocha palette ──────────────────────────────────────────────────
# Base      #1e1e2e  Crust     #11111b  Mantle    #181825
# Surface0  #313244  Surface1  #45475a  Surface2  #585b70
# Overlay0  #6c7086  Overlay1  #7f849c  Overlay2  #9399b2
# Subtext0  #a6adc8  Subtext1  #bac2de  Text      #cdd6f4
# Lavender  #b4befe  Blue      #89b4fa  Sapphire  #74c7ec
# Sky       #89dceb  Teal      #94e2d5  Green     #a6e3a1
# Yellow    #f9e2af  Peach     #fab387  Maroon    #eba0ac
# Red       #f38ba8  Mauve     #cba6f7  Pink      #f5c2e7
# Flamingo  #f2cdcd  Rosewater #f5e0dc
# ─────────────────────────────────────────────────────────────────────────────

ASCII_LOGO = r"""
 [bold #b4befe]╔═╗┌─┐┌┬┐┬┌┐┌┌─┐  ╔═╗┌─┐┌─┐┌┐┌┌┬┐[/bold #b4befe]
 [bold #89b4fa]║  │ │ ││││││ ┬  ╠═╣│ ┬├┤ │││ │ [/bold #89b4fa]
 [bold #74c7ec]╚═╝└─┘─┴┘┴┘└┘└─┘  ╩ ╩└─┘└─┘┘└┘ ┴ [/bold #74c7ec]
 [dim #6c7086]  autonomous coding intelligence  v0.1[/dim #6c7086]
"""

CSS = """
    /* ── Global ─────────────────────────────────────────────────────────────── */
    Screen {
        background: #1e1e2e;
        color: #cdd6f4;
        align: center middle;
        layers: base popup;
    }

    * {
        scrollbar-size: 1 1;
    }

    Scrollbar {
        background: transparent;
    }

    Scrollbar > .scrollbar-slider {
        background: #313244;
    }

    Scrollbar > .scrollbar-slider:hover {
        background: #45475a;
    }

    /* ── Mention popup ───────────────────────────────────────────────────────── */
    #mention-popup {
        display: none;
        layer: popup;
        width: 46;
        height: 12;
        background: #181825;
        border: solid #45475a;
        border-title-color: #b4befe;
        dock: bottom;
        margin-bottom: 5;
        margin-left: 2;
    }

    #mention-popup > .option-list--option {
        padding: 0 1;
        color: #bac2de;
    }

    #mention-popup > .option-list--option-highlighted {
        background: #313244;
        color: #b4befe;
    }

    /* ── Screen modes ────────────────────────────────────────────────────────── */
    Screen.chat-mode {
        align: left top;
    }

    /* ── App container ───────────────────────────────────────────────────────── */
    #app-container {
        width: 100%;
        max-width: 92;
        height: auto;
        align: center middle;
        layout: horizontal;
    }

    Screen.chat-mode #app-container {
        max-width: 100%;
        height: 100%;
        align: left top;
    }

    /* ── Main column ─────────────────────────────────────────────────────────── */
    #main-column {
        width: 1fr;
        height: auto;
        align: center middle;
    }

    Screen.chat-mode #main-column {
        width: 3fr;
        height: 100%;
        align: left top;
        padding-right: 0;
    }

    /* ── Sidebar ─────────────────────────────────────────────────────────────── */
    #sidebar {
        display: none;
        width: 1fr;
        max-width: 38;
        height: 100%;
        background: #181825;
        padding: 1 2;
        border-left: solid #313244;
    }

    Screen.chat-mode #sidebar {
        display: block;
    }

    /* ── Logo ─────────────────────────────────────────────────────────────────── */
    #logo-container {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-align: center;
        margin-bottom: 1;
        padding: 1 0;
    }

    Screen.chat-mode #logo-container {
        display: none;
    }

    #logo {
        text-align: center;
        width: 100%;
    }

    /* ── Chat container ──────────────────────────────────────────────────────── */
    #chat-container {
        width: 100%;
        height: auto;
        max-height: 50vh;
        background: transparent;
        padding: 0 1;
        margin-bottom: 0;
        display: none;
    }

    Screen.chat-mode #chat-container {
        display: block;
        height: 1fr;
        max-height: 100%;
        padding: 0 2;
    }

    /* ── Message styles ─────────────────────────────────────────────────────── */

    /* User message — right-side sky-blue left border + badge */
    .user-msg {
        border-left: thick #89dceb;
        background: #1e1e2e;
        padding: 0 1;
        margin: 1 0 0 0;
        color: #cdd6f4;
    }

    .user-msg-label {
        color: #89dceb;
        text-style: bold;
        margin-bottom: 0;
        padding: 0 1;
        margin-top: 1;
    }

    /* Agent message — mauve/lavender accent */
    .agent-msg-header {
        padding: 0 1;
        margin-top: 1;
        color: #6c7086;
    }

    .agent-msg {
        padding: 0 1;
        margin: 0 0 0 0;
        color: #cdd6f4;
        background: #1e1e2e;
    }

    /* Tool message — peach/amber accent */
    .tool-msg {
        border-left: thick #fab387;
        background: #181825;
        padding: 0 1;
        margin: 0 0 0 1;
        color: #a6adc8;
    }

    .tool-result-md {
        padding: 0 1;
        margin: 0 0 1 1;
        color: #9399b2;
    }

    /* System notice — teal subtle banner */
    .system-notice {
        background: #11111b;
        border-left: thick #94e2d5;
        padding: 0 1;
        margin: 1 0;
        color: #94e2d5;
    }

    /* ── Input card ──────────────────────────────────────────────────────────── */
    #input-card {
        width: 100%;
        height: auto;
        background: #181825;
        border: solid #313244;
        border-top: solid #45475a;
        padding: 1 2;
        margin: 0;
    }

    Screen.chat-mode #input-card {
        border-top: solid #b4befe;
        margin: 0 1 1 1;
    }

    #input-card:focus-within {
        border: solid #b4befe;
    }

    #prompt-input {
        background: #181825;
        border: none;
        color: #cdd6f4;
        padding: 0;
    }

    #prompt-input:focus {
        border: none;
        background: #181825;
    }

    /* ── Status line (home screen) ───────────────────────────────────────────── */
    #status-line {
        margin-top: 1;
        content-align: left middle;
        color: #6c7086;
        padding: 0 1;
    }

    Screen.chat-mode #status-line {
        display: none;
    }

    /* ── Shortcut / tip lines ────────────────────────────────────────────────── */
    #shortcuts-line {
        color: #585b70;
        content-align: left middle;
        margin-bottom: 1;
        padding-left: 1;
    }

    Screen.chat-mode #shortcuts-line {
        display: none;
    }

    #tip-line {
        color: #585b70;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    Screen.chat-mode #tip-line {
        display: none;
    }

    /* ── Footer (hidden on home) ────────────────────────────────────────────── */
    #footer-bar {
        display: none;
    }

    /* ── Input footer ──────────────────────────────────────────────────────── */
    #input-footer {
        display: none;
        width: 100%;
        height: auto;
        layout: horizontal;
        color: #585b70;
        margin-top: 1;
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

    /* ── Loading bar ────────────────────────────────────────────────────────── */
    #loading-bar {
        width: 18;
        color: #b4befe;
    }

    /* ── Sidebar sections ───────────────────────────────────────────────────── */
    .sb-section {
        margin-bottom: 0;
    }

    .sb-divider {
        color: #313244;
        margin: 1 0;
    }

    .sb-title {
        color: #b4befe;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }

    .sb-content {
        color: #6c7086;
        margin-bottom: 1;
        padding-left: 1;
    }

    #sb-tree {
        height: 1fr;
        border: none;
        background: transparent;
        padding-top: 1;
        color: #a6adc8;
    }

    #sb-tree > .tree--cursor {
        background: #313244;
        color: #cdd6f4;
    }

    #sb-tree > .tree--highlight {
        background: #45475a;
    }

    #sb-footer {
        dock: bottom;
        height: 2;
    }

    /* ── Progress bar (token tracker) ──────────────────────────────────────── */
    .token-bar {
        color: #a6e3a1;
        margin: 0;
        padding-left: 1;
    }

    .token-bar-warn {
        color: #f9e2af;
    }

    .token-bar-crit {
        color: #f38ba8;
    }
"""
