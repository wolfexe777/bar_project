from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import qrcode
from io import BytesIO
import os
from .models import UserProfile

def create_signed_qr_code(data, private_key):
    # Создание цифровой подписи
    signature = private_key.sign(
        data.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    # Создание QR-кода с подписью
    qr_data = f'{data}\n Цифровая подпись: {signature.hex()}'
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_bytes = BytesIO()
    qr_img.save(qr_bytes, format='PNG')
    qr_bytes.seek(0)

    # Генерируем имя файла на основе ID пользователя и номера телефона
    qr_code_filename = f"qr_code_{UserProfile.external_id}.png"
    qr_code_path = os.path.join("media", "qr_codes", qr_code_filename)

    # Сохраняем QR-код в файл
    with open(qr_code_path, 'wb') as f:
        f.write(qr_bytes.read())

    return qr_code_path