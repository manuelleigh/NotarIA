
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# --- NOTA DE SEGURIDAD ---
# Las siguientes credenciales están directamente en el código para facilitar este ejercicio.
# En un entorno de producción, DEBES usar variables de entorno para proteger esta información.
# Por ejemplo: os.environ.get('SMTP_USER')
SMTP_HOST = "mail.tesegnor.net.pe"
SMTP_PORT = 465
SMTP_USER = "mleigh@tesegnor.net.pe"
SMTP_PASS = "leigh%%2810%%" 
SENDER_NAME = "Asistente Notarial"

def send_password_reset_email(recipient_email: str, user_name: str, reset_link: str):
    """
    Envía un correo electrónico para restablecer la contraseña.
    """
    try:
        # --- Configuración del mensaje ---
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Restablece tu contraseña en Asistente Notarial"
        msg['From'] = f"{SENDER_NAME} <{SMTP_USER}>"
        msg['To'] = recipient_email

        # --- Contenido del correo (HTML) ---
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Hola {user_name},</h2>
                <p>Hemos recibido una solicitud para restablecer tu contraseña. Haz clic en el siguiente botón para continuar:</p>
                <p style="text-align: center; margin: 20px 0;">
                    <a href="{reset_link}" style="background-color: #007bff; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px;">
                        Restablecer Contraseña
                    </a>
                </p>
                <p>Si no solicitaste esto, puedes ignorar este correo de forma segura.</p>
                <hr>
                <p style="font-size: 0.9em; color: #777;">
                    Este enlace expirará en 1 hora.
                </p>
            </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        # --- Conexión y envío ---
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, recipient_email, msg.as_string())
        
        print(f"Correo de restablecimiento enviado exitosamente a {recipient_email}")
        return True, "Correo enviado"

    except smtplib.SMTPAuthenticationError as e:
        print(f"Error de autenticación SMTP: {e}")
        return False, "Error de autenticación con el servidor de correo. Revisa las credenciales."
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False, f"Error general al enviar el correo: {e}"

