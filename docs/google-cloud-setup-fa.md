# راه‌اندازی Google Cloud Text-to-Speech

این راهنما برای وقتی است که می‌خواهی provider گوگل را در همین پروژه فعال کنی.

## پیش‌نیاز

- یک حساب Google Cloud
- یک پروژه فعال در Google Cloud
- Billing فعال روی همان پروژه
- API زیر فعال باشد:
  - `Cloud Text-to-Speech API`

## روش سریع با `gcloud`

1. `gcloud` را نصب کن.
2. پروژه را انتخاب یا بساز:

```bash
gcloud init
```

3. لاگین مرورگری انجام بده:

```bash
gcloud auth login
```

4. Application Default Credentials را بساز:

```bash
gcloud auth application-default login
```

5. پروژه billing را روی ADC ست کن:

```bash
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

6. چک کن فایل credential ساخته شده باشد:

```bash
ls ~/.config/gcloud/application_default_credentials.json
```

اگر این فایل وجود داشت، provider گوگل در این پروژه می‌تواند از آن استفاده کند.

## روش جایگزین با service account

اگر خواستی مسیر production-تر داشته باشی:

1. در Google Cloud Console یک service account بساز.
2. برای آن JSON key بگیر.
3. فایل را روی سیستم نگه دار.
4. مسیرش را در `.env.local` یا shell ست کن:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```

یا داخل `tts_config.json`:

```json
{
  "providers": {
    "google": {
      "credentials_path": "/absolute/path/to/service-account.json"
    }
  }
}
```

## تست provider

```bash
source .venv/bin/activate
python synthesize_german_audio.py list-voices --provider google --language-code de-DE
python synthesize_german_audio.py synthesize --provider google --limit 10 --overwrite
```

## خطاهای رایج

- `quota project` تنظیم نشده:
  - مرحله `set-quota-project` را انجام بده.
- Billing فعال نیست:
  - در Cloud Console برای همان project، billing را روشن کن.
- API فعال نیست:
  - `Cloud Text-to-Speech API` را enable کن.
- فایل credential پیدا نمی‌شود:
  - یا `gcloud auth application-default login` را دوباره بزن یا `GOOGLE_APPLICATION_CREDENTIALS` را درست ست کن.
