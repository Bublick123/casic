import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from jinja2 import Template
import logging

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@casino.com")
    
    async def send_email(self, to_email: str, subject: str, html_content: str):
        """Отправка email"""
        try:
            message = MIMEMultipart("alternative")
            message["From"] = self.from_email
            message["To"] = to_email
            message["Subject"] = subject
            
            # Добавляем HTML контент
            message.attach(MIMEText(html_content, "html"))
            
            # Отправляем через SMTP
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=True
            )
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def render_template(self, template_name: str, context: dict) -> str:
        """Рендеринг HTML шаблона"""
        templates = {
            "win_notification": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; background-color: #f4f4f4; }
                    .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
                    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { padding: 20px; }
                    .win-amount { font-size: 24px; color: #27ae60; font-weight: bold; text-align: center; margin: 20px 0; }
                    .game-info { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Поздравляем с выигрышем!</h1>
                    </div>
                    <div class="content">
                        <p>Уважаемый игрок,</p>
                        <div class="win-amount">Вы выиграли ${{ amount }}!</div>
                        <div class="game-info">
                            <p><strong>Игра:</strong> {{ game_type }}</p>
                            <p><strong>Дата:</strong> {{ date }}</p>
                        </div>
                        <p>Спасибо, что играете в нашем казино!</p>
                        <p>С уважением,<br>Команда Casino</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            "deposit_confirmation": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; background-color: #f4f4f4; }
                    .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
                    .header { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
                    .content { padding: 20px; }
                    .amount { font-size: 24px; color: #2ecc71; font-weight: bold; text-align: center; margin: 20px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✅ Депозит подтвержден</h1>
                    </div>
                    <div class="content">
                        <p>Уважаемый игрок,</p>
                        <div class="amount">${{ amount }} зачислено на ваш счет</div>
                        <p>Теперь вы можете начать играть в наши игры!</p>
                        <p>Текущий баланс: ${{ balance }}</p>
                        <p>С уважением,<br>Команда Casino</p>
                    </div>
                </div>
            </body>
            </html>
            """
        }
        
        template_str = templates.get(template_name, "")
        if template_str:
            template = Template(template_str)
            return template.render(**context)
        return ""

# Глобальный инстанс
email_sender = EmailSender()