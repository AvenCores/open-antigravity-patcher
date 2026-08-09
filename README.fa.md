<div dir="rtl" lang="fa">

# Open AG Patcher

این فایل، راهنمای فارسی کوتاه برای استفاده از <span dir="ltr">Open AG Patcher</span> است.

<span dir="ltr">Open AG Patcher</span> یک پچر متن‌باز برای <span dir="ltr">Antigravity IDE</span>، <span dir="ltr">Antigravity 2.0</span> و <span dir="ltr">Antigravity CLI</span> یا همان <code dir="ltr">agy</code> است. این ابزار فایل‌های نصب‌شده روی همین سیستم را تغییر می‌دهد و قبل از تغییر، نسخه پشتیبان می‌سازد.

## نکته مهم

این پچ فقط محلی است؛ یعنی روی فایل‌های نصب‌شده در همین دستگاه اعمال می‌شود و وضعیت حساب <span dir="ltr">Google</span>، لایسنس، یا پاسخ‌های سمت سرور را تغییر نمی‌دهد.

اگر برنامه آپدیت شود، دوباره نصب شود، یا فایل باینری جایگزین شود، ممکن است لازم باشد پچ را دوباره اجرا کنید. اگر خطاهای سمت سرور مثل لایسنس نامعتبر یا محدودیت حساب دریافت می‌کنید، این پچر الزاماً نمی‌تواند آن را رفع کند.

## استفاده سریع

1. <span dir="ltr">Antigravity IDE</span>، <span dir="ltr">Antigravity 2.0</span> و <code dir="ltr">agy</code> را کامل ببندید.
2. ترمینال را با دسترسی <span dir="ltr">Administrator</span> باز کنید.
3. وارد پوشه <code dir="ltr">source</code> شوید.
4. وابستگی‌ها را نصب کنید.
5. اسکریپت را اجرا کنید.

</div>

```bash
pip install -r requirements.txt
python main.py
```

<div dir="rtl" lang="fa">

در منو می‌توانید یکی از گزینه‌های پچ یا بازگردانی را انتخاب کنید:

| گزینه | توضیح |
|---:|---|
| <code dir="ltr">1</code> | پچ <span dir="ltr">Antigravity IDE</span> برای فایل <code dir="ltr">main.js</code> |
| <code dir="ltr">2</code> | پچ <span dir="ltr">Antigravity 2.0</span> برای فایل <code dir="ltr">language_server</code> |
| <code dir="ltr">3</code> | پچ <span dir="ltr">Antigravity CLI</span> برای فایل <code dir="ltr">agy</code> یا <code dir="ltr">agy.exe</code> |
| <code dir="ltr">4</code> | بازگردانی پچ <span dir="ltr">Antigravity IDE</span> |
| <code dir="ltr">5</code> | بازگردانی پچ <span dir="ltr">Antigravity 2.0</span> |
| <code dir="ltr">6</code> | بازگردانی پچ <span dir="ltr">Antigravity CLI</span> |
| <code dir="ltr">9</code> | انتخاب مسیر دستی |

## اجرای مستقیم با مسیر

اگر تشخیص خودکار مسیر را پیدا نکرد، مسیر فایل یا پوشه نصب را مستقیم بدهید.

</div>

```bash
python main.py "C:\Users\<username>\AppData\Local\Programs\Antigravity IDE"
python main.py "C:\Users\<username>\AppData\Local\Programs\Antigravity\resources\bin\language_server.exe"
python main.py "C:\Users\<username>\AppData\Local\agy\bin\agy.exe"
```

<div dir="rtl" lang="fa">

## پچ Antigravity CLI

پچ <span dir="ltr">CLI</span> روی باینری <code dir="ltr">agy</code> یا <code dir="ltr">agy.exe</code> اعمال می‌شود و قبل از تغییر، فایل پشتیبان با پسوند <code dir="ltr">.agybak</code> می‌سازد.

در نسخه اصلاح‌شده <span dir="ltr">x86-64</span>، پچر فقط گیتی را تغییر می‌دهد که خطای <code dir="ltr">Eligibility check failed</code> را می‌سازد. یک بررسی مشابه در مسیر جزئیات خطا و سناریوی <span dir="ltr">logout/login</span> وجود دارد؛ آن بخش عمداً دست‌نخورده می‌ماند تا تعویض حساب و ورود دوباره خراب نشود.

اگر بعد از پچ کردن همچنان خطای حساب، لایسنس، یا محدودیت سمت سرور می‌بینید، احتمالاً مشکل از وضعیت حساب یا پاسخ سرور است، نه از فایل محلی.

## بازگردانی

برای بازگردانی از منو استفاده کنید:

</div>

```text
RESTORE -> 4, 5, or 6
```

<div dir="rtl" lang="fa">

برای <span dir="ltr">CLI</span>، فایل اصلی از نسخه پشتیبان <code dir="ltr">.agybak</code> برگردانده می‌شود.

## ساخت فایل اجرایی

در ویندوز:

</div>

```bash
cd source
pip install -r requirements.txt
pyinstaller --onefile --uac-admin --icon=icon.ico --name="Open_AG_Patcher_Windows" --noupx --clean --version-file=version.txt main.py
```

<div dir="rtl" lang="fa">

## عیب‌یابی کوتاه

اگر فایل قفل است، برنامه‌های <span dir="ltr">Antigravity</span> و پردازش <code dir="ltr">agy.exe</code> را ببندید و دوباره امتحان کنید.

اگر پچر مسیر نصب را پیدا نکرد، گزینه <code dir="ltr">9</code> را بزنید و مسیر را دستی وارد کنید.

اگر بعد از آپدیت برنامه پچ از بین رفت، دوباره پچر را اجرا کنید.

اگر خطای <code dir="ltr">Verification Required</code> هنگام تعویض حساب دیدید، مطمئن شوید از نسخه اصلاح‌شده پچر استفاده می‌کنید؛ نسخه اصلاح‌شده نباید مسیر <span dir="ltr">logout/login</span> را پچ کند.

</div>
