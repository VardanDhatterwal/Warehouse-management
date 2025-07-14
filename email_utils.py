
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Replace with your actual email and app password
SENDER_EMAIL = "vardandhatt.67@gmail.com"
APP_PASSWORD = "eahf vduo gqpm gwcj"  # App password from Gmail

def send_email(order, delivered=False):
    recipient = order['email']
    subject = "Order Delivered" if delivered else "Order Confirmation"
    status = "Delivered" if delivered else "Processing"

    # Build email body
    body = f"""
    Dear {order['customerName']},

    {'🎉 Your order has been delivered successfully!' if delivered else '🛒 Your order has been placed successfully.'}

    📦 Order ID: {order['orderId']}
    📅 Order Date: {order['timestamp']}
    🚚 Current Status: {status}

    🧾 Items Ordered:
    """

    for item in order['items']:
        body += f"\n- {item['name']} (Quantity: {item['quantity']})"

    body += "\n\nThank you for using our warehouse system!\n\nBest Regards,\nWarehouse Management Team"

    # Prepare email
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {recipient}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Replace with your actual email and app password
SENDER_EMAIL = "vardandhatt.67@gmail.com"
APP_PASSWORD = "eahf vduo gqpm gwcj"  # App password from Gmail

def send_email(order, delivered=False):
    recipient = order['email']
    subject = "Order Delivered" if delivered else "Order Confirmation"
    status = "Delivered" if delivered else "Processing"

    # Build email body
    body = f"""
    Dear {order['customerName']},

    {'🎉 Your order has been delivered successfully!' if delivered else '🛒 Your order has been placed successfully.'}

    📦 Order ID: {order['orderId']}
    📅 Order Date: {order['timestamp']}
    🚚 Current Status: {status}

    🧾 Items Ordered:
    """

    for item in order['items']:
        body += f"\n- {item['name']} (Quantity: {item['quantity']})"

    body += "\n\nThank you for using our warehouse system!\n\nBest Regards,\nWarehouse Management Team"

    # Prepare email
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {recipient}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

