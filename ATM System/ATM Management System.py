import json
import os
import random
import datetime
import time
import getpass

USERS_FILE = "users.json"
ATM_FILE = "atm_cash.json"

MIN_BALANCE = 1000
BLOCK_24_HOURS = 86400
DAILY_LIMIT = 20000


# ---------------- FILE HANDLING ----------------

def load_data(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)
    with open(file, "r") as f:
        return json.load(f)


def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


def today_date():
    return datetime.datetime.now().strftime("%d-%m-%Y")


def current_time():
    return datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


# ---------------- PIN STRENGTH ----------------

def is_strong_pin(pin):
    weak_patterns = ["0000", "1111", "1234", "4321", "2222", "9999"]

    if not pin.isdigit() or len(pin) != 4:
        return False
    if pin in weak_patterns:
        return False
    if len(set(pin)) == 1:
        return False
    if pin in "0123456789" or pin in "9876543210":
        return False

    return True


# ---------------- ATM CLASS ----------------

class ATM:

    def __init__(self):
        self.users = load_data(USERS_FILE)
        self.cash = load_data(ATM_FILE)
        self.current_user = None

        if not self.cash:
            self.cash = {"2000": 50, "500": 100, "200": 100, "100": 200}
            save_data(ATM_FILE, self.cash)

    # ---------------- CREATE USER ----------------
    def create_user(self):
        clear()
        print("===== CREATE NEW ATM CARD =====")

        name = input("Enter Account Holder Name: ")

        while True:
            card = str(random.randint(10**11, 10**12 - 1))
            if card not in self.users:
                break

        while True:
            pin = getpass.getpass("Set Strong 4 Digit PIN: ")
            if is_strong_pin(pin):
                break
            print("Weak PIN! Try stronger PIN.")

        while True:
            try:
                balance = int(input(f"Enter Initial Deposit (Min {MIN_BALANCE}): "))
                if balance >= MIN_BALANCE:
                    break
            except:
                pass
            print("Invalid amount!")

        self.users[card] = {
            "name": name,
            "pin": pin,
            "pin_history": [],
            "balance": balance,
            "blocked": False,
            "lock_until": 0,
            "failed_attempts": 0,
            "block_count": 0,
            "transactions": []
        }

        save_data(USERS_FILE, self.users)

        print("\n✅ ATM Card Created Successfully!")
        print("Card Number:", card)
        input("Press Enter...")

    # ---------------- LOGIN ----------------
    def login(self):
        clear()
        print("===== ATM LOGIN =====")

        card = input("Enter 12 Digit Card Number: ")

        if card not in self.users:
            print("Invalid Card!")
            time.sleep(2)
            return False

        user = self.users[card]

        if user["blocked"]:
            print("❌ Card Permanently Blocked!")
            time.sleep(2)
            return False

        if time.time() < user["lock_until"]:
            remaining = int(user["lock_until"] - time.time())
            print(f"⏳ Try after {remaining//3600}h {(remaining%3600)//60}m")
            time.sleep(2)
            return False

        while True:
            pin = getpass.getpass("Enter PIN: ")

            if pin == user["pin"]:
                user["failed_attempts"] = 0
                save_data(USERS_FILE, self.users)

                self.current_user = card
                print("Login Successful!")
                time.sleep(1)
                return True

            else:
                user["failed_attempts"] += 1
                attempts_left = 3 - user["failed_attempts"]

                print(f"❌ Wrong PIN! Attempts left: {attempts_left}")

                if user["failed_attempts"] >= 3:
                    user["failed_attempts"] = 0
                    user["block_count"] += 1

                    if user["block_count"] == 1:
                        user["lock_until"] = time.time() + BLOCK_24_HOURS
                        print("⚠️ Card Blocked for 24 Hours!")
                    else:
                        user["blocked"] = True
                        print("❌ Card Permanently Blocked!")

                    save_data(USERS_FILE, self.users)
                    time.sleep(2)
                    return False

                save_data(USERS_FILE, self.users)

    # ---------------- MENU ----------------
    def menu(self):
        last_activity = time.time()
        TIMEOUT = 30

        while True:
            if time.time() - last_activity > TIMEOUT:
                print("⚠️ Session Timeout! Auto Logout")
                time.sleep(2)
                break

            clear()
            print("===== ATM MENU =====")
            print("1. Balance Inquiry")
            print("2. Cash Withdrawal")
            print("3. Statement")
            print("4. Change PIN")
            print("5. Exit")

            choice = input("Select Option: ")
            last_activity = time.time()

            if choice == "1":
                self.balance()
            elif choice == "2":
                self.withdraw()
            elif choice == "3":
                self.full_statement()
            elif choice == "4":
                self.change_pin()
            elif choice == "5":
                break
            else:
                print("Invalid Option")
                time.sleep(2)

    # ---------------- BALANCE ----------------
    def balance(self):
        user = self.users[self.current_user]
        print("Available Balance:", user["balance"])

        if user["balance"] < 2000:
            print("⚠️ Low Balance Warning!")

        input("Press Enter...")

    # ---------------- WITHDRAW ----------------
    def withdraw(self):
        user = self.users[self.current_user]

        try:
            amount = int(input("Enter Amount (Multiple of 100): "))
        except:
            print("Invalid Input")
            time.sleep(2)
            return

        if amount <= 0 or amount % 100 != 0:
            print("Invalid Amount")
            time.sleep(2)
            return

        today = today_date()
        total_today = sum(
            txn["amount"] for txn in user["transactions"]
            if txn["type"] == "Withdraw" and txn["date"].startswith(today)
        )

        if total_today + amount > DAILY_LIMIT:
            print("Daily Limit Exceeded!")
            time.sleep(2)
            return

        if amount > user["balance"] - MIN_BALANCE:
            print("Minimum Balance Rule Violated")
            time.sleep(2)
            return

        amount_left = amount
        notes_used = {}

        for note in sorted(self.cash.keys(), key=int, reverse=True):
            note_val = int(note)
            count = min(amount_left // note_val, self.cash[note])

            if count > 0:
                notes_used[note] = count
                amount_left -= note_val * count
                self.cash[note] -= count

        if amount_left != 0:
            print("ATM does not have required notes!")
            return

        user["balance"] -= amount

        user["transactions"].append({
            "type": "Withdraw",
            "amount": amount,
            "date": current_time(),
            "balance_after": user["balance"]
        })

        save_data(USERS_FILE, self.users)
        save_data(ATM_FILE, self.cash)

        print("Notes Dispensed:")
        for n, c in notes_used.items():
            print(f"{n} x {c}")

        self.print_receipt("Withdraw", amount, user["balance"])
        input("Press Enter...")

    # ---------------- STATEMENT ----------------
    def full_statement(self):
        user = self.users[self.current_user]
        txns = user["transactions"]

        print("\n===== ACCOUNT STATEMENT =====")
        print(f"Name: {user['name']}")
        print(f"Current Balance: ₹{user['balance']}")
        print("----------------------------------------")

        if not txns:
            print("No Transactions Found")
        else:
            print("Date & Time         | Type     | Amount | Balance")
            print("----------------------------------------")
            for txn in txns:
                print(f"{txn['date']} | {txn['type']:8} | {txn['amount']:6} | {txn['balance_after']}")

        print("----------------------------------------")
        input("Press Enter...")

    # ---------------- RECEIPT ----------------
    def print_receipt(self, txn_type, amount, balance):
        user = self.users[self.current_user]

        receipt = f"""
------ ATM RECEIPT ------
Name: {user["name"]}
Type: {txn_type}
Amount: {amount}
Date: {current_time()}
Balance: {balance}
-------------------------
"""

        print(receipt)

        with open("receipts.txt", "a") as f:
            f.write(receipt + "\n")

    # ---------------- CHANGE PIN ----------------
    def change_pin(self):
        user = self.users[self.current_user]

        old = getpass.getpass("Enter Old PIN: ")
        if old != user["pin"]:
            print("Incorrect PIN")
            time.sleep(2)
            return

        new = getpass.getpass("Enter New PIN: ")

        if not is_strong_pin(new):
            print("Weak PIN!")
            time.sleep(2)
            return

        if new == user["pin"] or new in user["pin_history"]:
            print("Cannot reuse PIN!")
            time.sleep(2)
            return

        confirm = getpass.getpass("Confirm PIN: ")
        if new != confirm:
            print("Mismatch!")
            time.sleep(2)
            return

        user["pin_history"].append(user["pin"])
        user["pin_history"] = user["pin_history"][-5:]
        user["pin"] = new

        save_data(USERS_FILE, self.users)

        print("PIN Changed Successfully!")
        time.sleep(2)


# ---------------- RUN ----------------

atm = ATM()

while True:
    clear()
    print("===== PYTHON ATM SYSTEM =====")
    print("1. Create New ATM Card")
    print("2. Login")
    print("3. ATM Management (View/Add Cash)")
    print("4. Exit")

    choice = input("Select Option: ")

    if choice == "1":
        atm.create_user()

    elif choice == "2":
        if atm.login():
            atm.menu()

    elif choice == "3":
        while True:
            clear()
            print("===== ATM MANAGEMENT =====")
            print("1. View ATM Cash")
            print("2. Add Cash to ATM")
            print("3. Back")

            sub = input("Select Option: ")

            if sub == "1":
                print("\nATM Cash Available:")
                total_cash = 0

                for note, count in atm.cash.items():
                    print(f"{note} : {count} notes")
                    total_cash += int(note) * count

                print("\n-------------------------")
                print(f"💰 Total Cash in ATM: ₹{total_cash}")
                print("-------------------------")

                input("Press Enter...")

            elif sub == "2":
                print("\nAdd Cash to ATM")

                for note in atm.cash.keys():
                    try:
                        add = int(input(f"Enter number of {note} notes to add: "))
                        if add > 0:
                            atm.cash[note] += add
                    except:
                        print("Invalid input!")

                save_data(ATM_FILE, atm.cash)

                print("✅ Cash Added Successfully!")
                input("Press Enter...")

            elif sub == "3":
                break

            else:
                print("Invalid Option")
                time.sleep(2)

    elif choice == "4":
        confirm = input("Are you sure you want to exit? (y/n): ")
        if confirm.lower() == "y":
            print("Thank You!")
            break

    else:
        print("Invalid Option")
        time.sleep(2)
