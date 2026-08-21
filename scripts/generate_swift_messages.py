#!/usr/bin/env python3
# scripts/generate_swift_messages.py
"""
Generate synthetic SWIFT MT messages for NostroQ demonstration.

Creates realistic (but synthetic) SWIFT messages:
- MT103 (Single Customer Credit Transfer)
- MT202 (General Financial Institution Transfer)
- MT940 (Customer Statement Message)
- MT950 (Statement Message)

DISCLOSURE: All messages are synthetic. No real SWIFT traffic.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

random.seed(42)

OUTPUT_DIR = Path("data/swift_messages")


def generate_swift_header(msg_type: str, sender: str, receiver: str) -> Dict[str, str]:
    """Generate SWIFT message header."""
    return {
        "message_type": msg_type,
        "sender_bic": sender,
        "receiver_bic": receiver,
        "message_reference": f"{datetime.now().strftime('%Y%m%d')}{random.randint(100000, 999999)}",
        "creation_date": datetime.now().strftime("%y%m%d"),
        "creation_time": f"{random.randint(0, 23):02d}{random.randint(0, 59):02d}"
    }


def generate_mt103(
    sender_bic: str,
    receiver_bic: str,
    amount: float,
    currency: str,
    beneficiary_name: str
) -> Dict[str, Any]:
    """
    Generate MT103 Single Customer Credit Transfer.
    
    This is the most common SWIFT message for international payments.
    """
    reference = f"REF{random.randint(1000000, 9999999)}"
    
    return {
        "header": generate_swift_header("MT103", sender_bic, receiver_bic),
        "fields": {
            "20": reference,  # Transaction Reference
            "23B": "CRED",  # Bank Operation Code
            "32A": {  # Value Date, Currency, Amount
                "value_date": (datetime.now() + timedelta(days=random.choice([0, 1]))).strftime("%y%m%d"),
                "currency": currency,
                "amount": f"{amount:,.2f}"
            },
            "33B": {  # Currency/Instructed Amount
                "currency": currency,
                "amount": f"{amount:,.2f}"
            },
            "50K": {  # Ordering Customer
                "account": f"/{''.join(random.choices('0123456789', k=10))}",
                "name": f"COMPANY {random.randint(100, 999)} LTD",
                "address": "123 BUSINESS STREET",
                "city": "CITY"
            },
            "52A": sender_bic,  # Ordering Institution
            "53A": receiver_bic,  # Sender's Correspondent
            "57A": receiver_bic,  # Account With Institution
            "59": {  # Beneficiary
                "account": f"/{''.join(random.choices('0123456789', k=10))}",
                "name": beneficiary_name,
                "address": "456 BENEFICIARY ROAD"
            },
            "70": f"/INV/{reference}/PAYMENT FOR SERVICES",  # Remittance Information
            "71A": "SHA",  # Details of Charges (Shared)
            "72": "/ACC/REGULAR PAYMENT"  # Sender to Receiver Info
        },
        "raw_message": generate_mt103_raw(reference, amount, currency, sender_bic, receiver_bic, beneficiary_name),
        "synthetic": True
    }


def generate_mt103_raw(ref: str, amount: float, currency: str, sender: str, receiver: str, beneficiary: str) -> str:
    """Generate raw MT103 message format."""
    value_date = (datetime.now() + timedelta(days=1)).strftime("%y%m%d")
    
    return f""":20:{ref}
:23B:CRED
:32A:{value_date}{currency}{amount:,.2f}
:33B:{currency}{amount:,.2f}
:50K:/1234567890
ORDERING COMPANY LTD
123 BUSINESS STREET
:52A:{sender}
:57A:{receiver}
:59:/0987654321
{beneficiary}
456 BENEFICIARY ROAD
:70:/INV/{ref}/PAYMENT
:71A:SHA"""


def generate_mt202(
    sender_bic: str,
    receiver_bic: str,
    amount: float,
    currency: str
) -> Dict[str, Any]:
    """
    Generate MT202 General Financial Institution Transfer.
    
    Used for bank-to-bank transfers (cover payments).
    """
    reference = f"COV{random.randint(1000000, 9999999)}"
    related_ref = f"REF{random.randint(1000000, 9999999)}"
    
    return {
        "header": generate_swift_header("MT202", sender_bic, receiver_bic),
        "fields": {
            "20": reference,  # Transaction Reference
            "21": related_ref,  # Related Reference
            "32A": {
                "value_date": (datetime.now() + timedelta(days=1)).strftime("%y%m%d"),
                "currency": currency,
                "amount": f"{amount:,.2f}"
            },
            "52A": sender_bic,  # Ordering Institution
            "58A": receiver_bic,  # Beneficiary Institution
            "72": "/BNF/COVER FOR MT103"
        },
        "synthetic": True
    }


def generate_mt940(
    account_bic: str,
    account_number: str,
    currency: str,
    opening_balance: float,
    transactions: List[Dict]
) -> Dict[str, Any]:
    """
    Generate MT940 Customer Statement Message.
    
    Used for end-of-day account statements.
    """
    closing_balance = opening_balance + sum(
        t["amount"] if t["type"] == "C" else -t["amount"] 
        for t in transactions
    )
    
    return {
        "header": generate_swift_header("MT940", account_bic, "CUSTXXXX"),
        "fields": {
            "20": f"STMT{datetime.now().strftime('%Y%m%d')}",  # Transaction Reference
            "25": f"{account_bic[:8]}/{account_number}",  # Account Identification
            "28C": f"{random.randint(1, 365):03d}/1",  # Statement Number
            "60F": {  # Opening Balance
                "dc_mark": "C" if opening_balance >= 0 else "D",
                "date": datetime.now().strftime("%y%m%d"),
                "currency": currency,
                "amount": f"{abs(opening_balance):,.2f}"
            },
            "61": transactions,  # Statement Lines
            "62F": {  # Closing Balance
                "dc_mark": "C" if closing_balance >= 0 else "D",
                "date": datetime.now().strftime("%y%m%d"),
                "currency": currency,
                "amount": f"{abs(closing_balance):,.2f}"
            },
            "64": {  # Closing Available Balance
                "dc_mark": "C" if closing_balance >= 0 else "D",
                "date": datetime.now().strftime("%y%m%d"),
                "currency": currency,
                "amount": f"{abs(closing_balance):,.2f}"
            }
        },
        "synthetic": True
    }


def generate_statement_transaction(currency: str) -> Dict[str, Any]:
    """Generate a single statement transaction line."""
    tx_type = random.choice(["C", "D"])  # Credit or Debit
    amount = random.uniform(10000, 5000000)
    
    return {
        "value_date": datetime.now().strftime("%y%m%d"),
        "entry_date": datetime.now().strftime("%m%d"),
        "type": tx_type,
        "amount": round(amount, 2),
        "currency": currency,
        "transaction_type": random.choice(["TRF", "CHK", "RTN", "INT"]),
        "reference": f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=16))}",
        "supplementary_details": f"/{random.choice(['PAYMENT', 'TRANSFER', 'FEE', 'INTEREST'])}"
    }


def generate_sample_messages() -> Dict[str, List[Dict]]:
    """Generate sample SWIFT messages for all types."""
    
    messages = {
        "mt103": [],
        "mt202": [],
        "mt940": []
    }
    
    # Sample BICs
    bics = {
        "USD": ["CHASUS33", "CITIUS33", "BOFAUS3N"],
        "EUR": ["DEUTDEFF", "BNPAFRPP", "INGBNL2A"],
        "GBP": ["BARCGB22", "MIDLGB22", "LOYDGB2L"],
        "INR": ["HDFCINBB", "ABORINBB", "SBININBB"]
    }
    
    beneficiaries = [
        "GLOBAL TRADING CO LTD",
        "INTERNATIONAL SUPPLIERS INC",
        "EXPORT SERVICES PVT LTD",
        "TECH SOLUTIONS GMBH",
        "ASIA PACIFIC TRADERS"
    ]
    
    # Generate MT103 messages (10 samples)
    for _ in range(10):
        currency = random.choice(["USD", "EUR", "GBP"])
        amount = random.uniform(50000, 10000000)
        sender = random.choice(bics[currency])
        receiver = random.choice(bics["INR"])
        beneficiary = random.choice(beneficiaries)
        
        messages["mt103"].append(
            generate_mt103(sender, receiver, amount, currency, beneficiary)
        )
    
    # Generate MT202 messages (5 samples)
    for _ in range(5):
        currency = random.choice(["USD", "EUR", "GBP"])
        amount = random.uniform(1000000, 50000000)
        sender = random.choice(bics[currency])
        receiver = random.choice(bics["INR"])
        
        messages["mt202"].append(
            generate_mt202(sender, receiver, amount, currency)
        )
    
    # Generate MT940 statements (3 samples)
    for currency in ["USD", "EUR", "INR"]:
        account_bic = random.choice(bics.get(currency, bics["USD"]))
        account_number = "".join(random.choices("0123456789", k=12))
        opening_balance = random.uniform(10000000, 100000000)
        
        # Generate 5-10 transactions
        transactions = [
            generate_statement_transaction(currency)
            for _ in range(random.randint(5, 10))
        ]
        
        messages["mt940"].append(
            generate_mt940(account_bic, account_number, currency, opening_balance, transactions)
        )
    
    return messages


def main():
    """Generate SWIFT message samples."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Generating synthetic SWIFT messages...")
    
    messages = generate_sample_messages()
    
    # Save each message type
    for msg_type, msg_list in messages.items():
        filepath = OUTPUT_DIR / f"{msg_type}_samples.json"
        with open(filepath, "w") as f:
            json.dump(msg_list, f, indent=2)
        print(f"  ✓ Generated {len(msg_list)} {msg_type.upper()} messages")
    
    # Save combined file
    combined_file = OUTPUT_DIR / "all_messages.json"
    with open(combined_file, "w") as f:
        json.dump(messages, f, indent=2)
    
    print(f"\n✅ SWIFT message generation complete!")
    print(f"   Output: {OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
