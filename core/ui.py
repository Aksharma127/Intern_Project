import time


class UI:
    # ANSI Colors
    # ANSI Colors
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    @staticmethod
    def banner():
        print(f"{UI.CYAN}")
        print("╔════════════════════════════════════════════════════════╗")
        print("║     NIYAMRAI AGENT ORCHESTRATOR v1.0 (DEMO)             ║")
        print("║   Autonomic Invoice Reconciliation System               ║")
        print("╚════════════════════════════════════════════════════════╝")
        print(f"{UI.RESET}")
        time.sleep(0.5)

    @staticmethod
    def section(name):
        print(f"\n{UI.HEADER}>>> INITIATING PROTOCOL: {name.upper()} <<<{UI.RESET}")
        print("-" * 60)
        time.sleep(0.5)

    @staticmethod
    def log(agent, message, status="INFO"):
        """
        agent: Name of the agent (e.g., 'Extractor')
        status: INFO, SUCCESS, WARNING, ERROR, THINKING
        """

        icons = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "THINKING": "🧠"
        }

        colors = {
            "INFO": UI.RESET,
            "SUCCESS": UI.GREEN,
            "WARNING": UI.YELLOW,
            "ERROR": UI.RED,
            "THINKING": UI.CYAN
        }

        timestamp = time.strftime("%H:%M:%S")
        color = colors.get(status, UI.RESET)
        icon = icons.get(status, "•")

        print(f"{UI.BOLD}[{timestamp}]{UI.RESET} {UI.BLUE}[{agent}]{UI.RESET} {icon} {color}{message}{UI.RESET}")

        if status == "THINKING":
            time.sleep(0.8)

    @staticmethod
    def show_discrepancy(item, inv_price, po_price):
        """Visually highlight a price trap"""
        diff = ((inv_price - po_price) / po_price) * 100 if po_price else 0.0
        print(f"\n    {UI.RED}┌───────────────────────────────────────────────┐")
        print(f"    │  ⚠ DISCREPANCY DETECTED: {item:<20} │")
        print(f"    │  Invoice Price: £{inv_price:<24} │")
        print(f"    │  PO Price:      £{po_price:<24} │")
        print(f"    │  Difference:    +{diff:.1f}% (Tolerance: 5%)      │")
        print(f"    └───────────────────────────────────────────────┘{UI.RESET}\n")
        time.sleep(1)

    @staticmethod
    def show_decision(action, confidence, reason):
        color = UI.GREEN if action == "auto_approve" else UI.RED
        if action == "flag_for_review":
            color = UI.YELLOW

        print(f"\n{UI.BOLD}══════════════════ FINAL DECISION ══════════════════{UI.RESET}")
        print(f"ACTION:     {color}{action.upper()}{UI.RESET}")
        print(f"CONFIDENCE: {confidence * 100:.1f}%")
        print(f"REASON:     {reason}")
        print(f"{UI.BOLD}════════════════════════════════════════════════════{UI.RESET}\n")
