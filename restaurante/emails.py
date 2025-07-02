
# from django.conf import settings
# from djoser.email import PasswordResetEmail

# class CustomPasswordResetEmail(PasswordResetEmail):
#     def get_context_data(self):
#         context = super().get_context_data()
#         context["domain"] = settings.DJOSER.get("DOMAIN", "localhost:3000")
#         context["protocol"] = settings.DJOSER.get("PROTOCOL", "http")
#         context["site_name"] = settings.DJOSER.get("SITE_NAME", context["domain"])
#         return context


from django.conf import settings
from djoser.email import PasswordResetEmail

class CustomPasswordResetEmail(PasswordResetEmail):
    def get_context_data(self):
        context = super().get_context_data()
        # Safely pull from DJOSER dict or fallback
        djoser_config = getattr(settings, "DJOSER", {})
        context["domain"] = djoser_config.get("DOMAIN") or "localhost:3000"
        context["protocol"] = djoser_config.get("PROTOCOL") or "http"
        context["site_name"] = djoser_config.get("SITE_NAME") or context["domain"]

        # print("=== PASSWORD RESET EMAIL CONTEXT ===")
        # print("domain:", context["domain"])
        # print("protocol:", context["protocol"])
        # print("site_name:", context["site_name"])
        # print("===================================")

        return context









#IF IN CASE ONE WANTS TO REVISIT THE TEMPLATES



# from django.conf import settings
# from djoser.email import PasswordResetEmail
# from django.utils import timezone

# class CustomPasswordResetEmail(PasswordResetEmail):
#     def get_context_data(self):
#         context = super().get_context_data()
#         context["frontend_url"] = settings.FRONTEND_URL
#         context["username"] = self.context.get("user").get_username()
#         context["now"] = timezone.now()
#         print("=== LIVE CONTEXT ===")
#         for key, value in context.items():
#             print(f"{key}: {value}")
#         print("=== END CONTEXT ===")
#         return context

# restaurante/emails.py



# from django.conf import settings
# from django.utils import timezone
# from djoser.email import PasswordResetEmail
# from django.core.mail import EmailMultiAlternatives

# class CustomPasswordResetEmail(PasswordResetEmail):
#     def get_context_data(self):
#         context = super().get_context_data()
#         context["frontend_url"] = settings.FRONTEND_URL
#         context["username"] = self.context.get("user")
#         context["now"] = timezone.now()
#         return context

#     def get_email_message(self, to):
#         context = self.get_context_data()
#         html_content = self.template.render(context)
#         subject = self.get_subject()
#         print("=== ACTUAL EMAIL BEING SENT ===")
#         print(html_content)
#         print("=== END ===")
#         message = EmailMultiAlternatives(subject=subject, body=html_content, to=to)
#         message.attach_alternative(html_content, "text/html")
#         return message

#     # def send(self, to):
#     #     context = self.get_context_data()
#     #     html_content = self.template.render(context)
#     #     subject = self.get_subject()
#     #     from_email = settings.DEFAULT_FROM_EMAIL

#     #     print("=== FINAL EMAIL RENDER ===")
#     #     print(html_content)
#     #     print("=== END RENDER ===")

#     #     # Create email with BOTH plain + HTML (fallback)
#     #     email_message = EmailMultiAlternatives(
#     #         subject=subject,
#     #         body=html_content,  # fallback body
#     #         from_email=from_email,
#     #         to=to
#     #     )
#     #     email_message.attach_alternative(html_content, "text/html")
#     #     email_message.send()
