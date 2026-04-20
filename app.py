from flask import Flask, render_template, request, redirect, url_for, session, Response
import mysql.connector
import os
from dotenv import load_dotenv
from flask_mail import Mail, Message

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key")

# ---------------- MAIL CONFIG ----------------
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_USERNAME")

mail = Mail(app)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html", active_page="home")


# ---------------- SERVICES ----------------
@app.route("/services")
def services():
    return render_template("services.html", active_page="services")


# ---------------- ABOUT ----------------
@app.route("/about")
def about():
    return render_template("about.html", active_page="about")


# ---------------- CONTACT ----------------
@app.route("/contact", methods=["GET", "POST"])
def contact():
    success = None

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        service = request.form.get("service")
        message = request.form.get("message")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            query = """
                INSERT INTO contact_enquiries (name, email, phone, service, message)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (name, email, phone, service, message)
            cursor.execute(query, values)
            conn.commit()

            cursor.close()
            conn.close()

            # -------- SEND EMAIL TO ADMIN --------
            admin_email = os.getenv("ADMIN_RECEIVER")

            mail_subject = f"New Enquiry from {name} | Night Echo Works"
            mail_body = f"""
New enquiry received from Night Echo Works website.

Name: {name}
Email: {email}
Phone: {phone}
Service: {service}

Message:
{message}
"""

            msg = Message(
                subject=mail_subject,
                recipients=[admin_email],
                body=mail_body
            )
            mail.send(msg)

            success = "Your enquiry has been sent successfully!"

        except Exception as e:
            print("Error:", e)
            success = "Something went wrong. Please try again."

    return render_template("contact.html", active_page="contact", success=success)


# ---------------- ADMIN LOGIN ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query = "SELECT * FROM admin WHERE username=%s AND password=%s"
            cursor.execute(query, (username, password))
            admin_user = cursor.fetchone()

            cursor.close()
            conn.close()

            if admin_user:
                session["admin_logged_in"] = True
                session["admin_username"] = admin_user["username"]
                return redirect(url_for("dashboard"))
            else:
                error = "Invalid username or password"

        except Exception as e:
            print("Error:", e)
            error = "Something went wrong. Please try again."

    return render_template("admin.html", error=error)


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    search = request.args.get("search", "").strip()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if search:
            query = """
                SELECT * FROM contact_enquiries
                WHERE name LIKE %s
                   OR email LIKE %s
                   OR phone LIKE %s
                   OR service LIKE %s
                   OR message LIKE %s
                ORDER BY id DESC
            """
            search_value = f"%{search}%"
            cursor.execute(query, (search_value, search_value, search_value, search_value, search_value))
        else:
            query = "SELECT * FROM contact_enquiries ORDER BY id DESC"
            cursor.execute(query)

        enquiries = cursor.fetchall()

        count_query = "SELECT COUNT(*) AS total FROM contact_enquiries"
        cursor.execute(count_query)
        total_result = cursor.fetchone()
        total_enquiries = total_result["total"]

        cursor.close()
        conn.close()

        return render_template(
            "dashboard.html",
            enquiries=enquiries,
            total_enquiries=total_enquiries,
            search=search
        )

    except Exception as e:
        print("Error:", e)
        return render_template(
            "dashboard.html",
            enquiries=[],
            total_enquiries=0,
            search=search
        )


# ---------------- DELETE ----------------
@app.route("/delete/<int:enquiry_id>")
def delete_enquiry(enquiry_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contact_enquiries WHERE id=%s", (enquiry_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error:", e)

    return redirect(url_for("dashboard"))


@app.route("/sitemap.xml")
def sitemap():
    return Response("""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">

<url>
  <loc>https://night-echo-works.onrender.com/</loc>
</url>

<url>
  <loc>https://night-echo-works.onrender.com/services</loc>
</url>

<url>
  <loc>https://night-echo-works.onrender.com/about</loc>
</url>

<url>
  <loc>https://night-echo-works.onrender.com/contact</loc>
</url>

</urlset>
""", mimetype='application/xml')

@app.route("/robots.txt")
def robots():
    return """User-agent: *
Allow: /

Sitemap: https://night-echo-works.onrender.com/sitemap.xml
"""


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True)