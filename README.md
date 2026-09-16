# YouTube Shorts Automation Script

Bu loyiha har kuni avtomatik tarzda YouTube Shorts tayyorlab, kanalingga yuklash uchun mo'ljallangan. Skript quyidagi jarayonlarni bajaradi:

- Gemini API orqali 30-50 soniya bo'lgan qiziqarli faktlar ssenariysi va YouTube title/description/hashtags yaratadi.
- gTTS orqali matnni MP3 audio faylga aylantiradi.
- Pexels API orqali 9:16 formatdagi orqa fon video yuklaydi.
- MoviePy yordamida video va audio birlashtirib 1080x1920 Shorts video tayyorlaydi.
- YouTube Data API v3 orqali videoni avtomatik yuklaydi.
- `schedule` kutubxonasi bilan har kuni soat 18:00 da ishga tushadi.

## Loyihani yuklash

```bash
cd "c:\Users\0\Documents\Youtube avto"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## API kalitlarini sozlash

1. `.env.example` faylini `.env` deb nomlang.
2. Quyidagi ma'lumotlarni to'ldiring:

```env
GEMINI_API_KEY=your_gemini_api_key_here
PEXELS_API_KEY=your_pexels_api_key_here
YOUTUBE_CLIENT_SECRETS_FILE=client_secret.json
YOUTUBE_CREDENTIALS_FILE=credentials.json
YOUTUBE_CHANNEL_ID=
UPLOAD_PRIVACY=private
DEFAULT_TOPIC=interesting facts
SCHEDULE_TIME=18:00
```

## Google Cloud / YouTube uchun talablar

1. Google Cloud Console da yangi loyiha yarating.
2. `YouTube Data API v3` ni yoqing.
3. OAuth client ID yaratib `client_secret.json` faylini yuklab oling.
4. Faylni loyiha rootiga joylang: `client_secret.json`.
5. Ilk marta skript ishga tushganda OAuth browser oynasida login qilishingiz kerak bo'ladi.

## Gemini API uchun

- Google AI Studio orqali API key oling.
- Keyni `.env` faylga yozing.

## Pexels API uchun

- Pexels developers sahifasidan API key oling.
- Keyni `.env` faylga yozing.

## Skriptni tekshirish

Bir martalik ishlatish uchun:

```bash
python youtube_automation.py --once
```

Har kuni soat 18:00 avtomatik ishlash uchun:

```bash
python youtube_automation.py
```

Skript to'xtatilganda `Ctrl + C` bilan chiqib ketishingiz mumkin.

## Fayl tuzilmasi

```text
Youtube avto/
├── .env
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── youtube_automation.py
├── output/
└── assets/
```

## Muhim eslatma

- `UPLOAD_PRIVACY` default qiymati `private` bo'lib, u video avtomatik tarzda shaxsiy ko'rinishda yuklanadi.
- Rasmuylik uchun videoni ommaga chiqarishdan avval `public` yoki `unlisted` qilib o'zgartiring.
- Agar gTTS ishlamasa, `edge-tts` o'rniga `gTTS` ishlatiladi. Hozirgi skenario gTTS bilan ishlaydi.

## Muammolar

Agar YouTube upload qismida xatolik chiqsa, quyidagilarni tekshiring:

- Google Cloud projectda API yoqilganmi?
- OAuth client ID to'g'ri ishlatilayotganmi?
- `client_secret.json` loyihada mavjudmi?
- YouTube kanaliga ruxsat berilganmi?

## Foydali xotiralar

- Avtomatik ishga tushish uchun Windowsda `Task Scheduler` ham ishlatishingiz mumkin.
- Skriptni production holatda ishlatishda `private` o'rniga `public` ishlatishingiz mumkin.
