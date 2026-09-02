import html

import httpx

from app.core.config import settings


class EmailService:

    BREVO_URL = (
        "https://api.brevo.com/v3/smtp/email"
    )


    # =========================
    # ENVIAR EMAIL
    # =========================

    @staticmethod
    def send_email(
        *,
        to_email: str,
        to_name: str | None,
        subject: str,
        html_content: str,
    ) -> None:

        payload = {
            "sender": {
                "name": settings.brevo_sender_name,
                "email": settings.brevo_sender_email,
            },

            "to": [
                {
                    "email": to_email,

                    **(
                        {
                            "name": to_name,
                        }
                        if to_name
                        else {}
                    ),
                }
            ],

            "subject": subject,

            "htmlContent": html_content,
        }


        headers = {
            "accept": "application/json",

            "content-type":
                "application/json",

            "api-key":
                settings.brevo_api_key,
        }


        try:
            with httpx.Client(
                timeout=15.0,
            ) as client:
                response = client.post(
                    EmailService.BREVO_URL,

                    headers=headers,

                    json=payload,
                )

        except httpx.RequestError as error:
            raise RuntimeError(
                "No se pudo conectar con el servicio de correo"
            ) from error


        if response.status_code not in (
            200,
            201,
            202,
        ):
            try:
                detail = response.json()
            except Exception:
                detail = response.text

            raise RuntimeError(
                f"Brevo rechazó el correo: {detail}"
            )


    # =========================
    # CÓDIGO DE VERIFICACIÓN
    # =========================

    @staticmethod
    def send_verification_code(
        *,
        email: str,
        first_name: str,
        code: str,
    ) -> None:

        safe_name = html.escape(
            first_name
        )

        safe_code = html.escape(
            code
        )


        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>
                Verifica tu cuenta de Sonelya
            </title>
        </head>

        <body
            style="
                margin: 0;
                padding: 0;
                background-color: #080808;
                font-family: Arial, Helvetica, sans-serif;
            "
        >

            <table
                width="100%"
                cellspacing="0"
                cellpadding="0"
                style="
                    background-color: #080808;
                    padding: 40px 16px;
                "
            >

                <tr>
                    <td align="center">

                        <table
                            width="100%"
                            cellspacing="0"
                            cellpadding="0"
                            style="
                                max-width: 520px;
                                background-color: #151515;
                                border-radius: 24px;
                                overflow: hidden;
                            "
                        >

                            <tr>
                                <td
                                    style="
                                        padding: 40px 32px;
                                        text-align: center;
                                    "
                                >

                                    <div
                                        style="
                                            font-size: 32px;
                                            font-weight: 800;
                                            color: #FFFFFF;
                                            margin-bottom: 8px;
                                        "
                                    >
                                        Sonelya
                                    </div>


                                    <div
                                        style="
                                            font-size: 14px;
                                            color: #9A9A9A;
                                            margin-bottom: 32px;
                                        "
                                    >
                                        Tu música. Tu espacio.
                                    </div>


                                    <div
                                        style="
                                            font-size: 24px;
                                            font-weight: 700;
                                            color: #FFFFFF;
                                            margin-bottom: 14px;
                                        "
                                    >
                                        Verifica tu correo
                                    </div>


                                    <div
                                        style="
                                            font-size: 15px;
                                            line-height: 1.6;
                                            color: #B8B8B8;
                                            margin-bottom: 28px;
                                        "
                                    >
                                        Hola {safe_name},
                                        usa este código para verificar
                                        tu cuenta de Sonelya.
                                    </div>


                                    <div
                                        style="
                                            display: inline-block;
                                            background-color: #2F80FF;
                                            color: #FFFFFF;
                                            font-size: 34px;
                                            font-weight: 800;
                                            letter-spacing: 8px;
                                            padding: 18px 24px;
                                            border-radius: 16px;
                                            margin-bottom: 28px;
                                        "
                                    >
                                        {safe_code}
                                    </div>


                                    <div
                                        style="
                                            font-size: 13px;
                                            color: #8A8A8A;
                                            line-height: 1.6;
                                        "
                                    >
                                        Este código expira en
                                        <strong
                                            style="
                                                color: #FFFFFF;
                                            "
                                        >
                                            10 minutos
                                        </strong>.
                                    </div>


                                    <div
                                        style="
                                            margin-top: 16px;
                                            font-size: 12px;
                                            color: #686868;
                                            line-height: 1.5;
                                        "
                                    >
                                        Si tú no creaste esta cuenta,
                                        puedes ignorar este mensaje.
                                    </div>

                                </td>
                            </tr>

                        </table>

                    </td>
                </tr>

            </table>

        </body>
        </html>
        """


        EmailService.send_email(
            to_email=email,

            to_name=first_name,

            subject=(
                f"{safe_code} es tu código de Sonelya"
            ),

            html_content=html_content,
        )

    # =========================
    # CÓDIGO RECUPERAR CONTRASEÑA
    # =========================

    @staticmethod
    def send_password_reset_code(
            *,
            email: str,
            first_name: str,
            code: str,
    ) -> None:

        safe_name = html.escape(
            first_name
        )

        safe_code = html.escape(
            code
        )

        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>
                Recupera tu contraseña de Sonelya
            </title>
        </head>

        <body
            style="
                margin: 0;
                padding: 0;
                background-color: #080808;
                font-family: Arial, Helvetica, sans-serif;
            "
        >

            <table
                width="100%"
                cellspacing="0"
                cellpadding="0"
                style="
                    background-color: #080808;
                    padding: 40px 16px;
                "
            >

                <tr>
                    <td align="center">

                        <table
                            width="100%"
                            cellspacing="0"
                            cellpadding="0"
                            style="
                                max-width: 520px;
                                background-color: #151515;
                                border-radius: 24px;
                                overflow: hidden;
                            "
                        >

                            <tr>
                                <td
                                    style="
                                        padding: 40px 32px;
                                        text-align: center;
                                    "
                                >

                                    <div
                                        style="
                                            font-size: 32px;
                                            font-weight: 800;
                                            color: #FFFFFF;
                                            margin-bottom: 8px;
                                        "
                                    >
                                        Sonelya
                                    </div>


                                    <div
                                        style="
                                            font-size: 14px;
                                            color: #9A9A9A;
                                            margin-bottom: 32px;
                                        "
                                    >
                                        Tu música. Tu espacio.
                                    </div>


                                    <div
                                        style="
                                            font-size: 24px;
                                            font-weight: 700;
                                            color: #FFFFFF;
                                            margin-bottom: 14px;
                                        "
                                    >
                                        Recupera tu contraseña
                                    </div>


                                    <div
                                        style="
                                            font-size: 15px;
                                            line-height: 1.6;
                                            color: #B8B8B8;
                                            margin-bottom: 28px;
                                        "
                                    >
                                        Hola {safe_name},
                                        recibimos una solicitud
                                        para cambiar la contraseña
                                        de tu cuenta de Sonelya.
                                    </div>


                                    <div
                                        style="
                                            display: inline-block;
                                            background-color: #2F80FF;
                                            color: #FFFFFF;
                                            font-size: 34px;
                                            font-weight: 800;
                                            letter-spacing: 8px;
                                            padding: 18px 24px;
                                            border-radius: 16px;
                                            margin-bottom: 28px;
                                        "
                                    >
                                        {safe_code}
                                    </div>


                                    <div
                                        style="
                                            font-size: 13px;
                                            color: #8A8A8A;
                                            line-height: 1.6;
                                        "
                                    >
                                        Este código expira en
                                        <strong
                                            style="
                                                color: #FFFFFF;
                                            "
                                        >
                                            10 minutos
                                        </strong>.
                                    </div>


                                    <div
                                        style="
                                            margin-top: 16px;
                                            font-size: 12px;
                                            color: #686868;
                                            line-height: 1.5;
                                        "
                                    >
                                        Si tú no solicitaste cambiar
                                        tu contraseña, puedes ignorar
                                        este mensaje.
                                    </div>

                                </td>
                            </tr>

                        </table>

                    </td>
                </tr>

            </table>

        </body>
        </html>
        """

        EmailService.send_email(
            to_email=email,

            to_name=first_name,

            subject=(
                f"{safe_code} es tu código "
                f"para recuperar Sonelya"
            ),

            html_content=html_content,
        )