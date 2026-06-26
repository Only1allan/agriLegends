---
name: farmwise-integrations
description: External API integration patterns for FarmWise. Use when integrating AgroMonitoring, iSDAsoil, Twilio WhatsApp/SMS, or Masumi Cardano SDK. Triggers on API integration tasks.
---

# FarmWise Integration Patterns

## AgroMonitoring (Satellite + Weather)

### NDVI History
```
GET https://api.agromonitoring.com/agro/1.0/ndvi/history
  ?polyid={polygon_id}&start={unix_start}&end={unix_end}&appid={key}
Response: [{dt, source, dc, cl, data: {std, p25, min, max, median, mean, num}}]
```

### Create Polygon
```
POST https://api.agromonitoring.com/agro/1.0/polygons?appid={key}
Body: GeoJSON Feature with Polygon geometry
```

### Weather
```
GET https://api.agromonitoring.com/agro/1.0/weather?lat={lat}&lon={lon}&appid={key}
```

### Accumulated Temperature (GDD)
```
GET https://api.agromonitoring.com/agro/1.0/accumulated_temperature
  ?polyid={id}&start={start}&end={end}&appid={key}&threshold=8
```

## iSDAsoil (Soil Baseline)
```
GET https://api.isda-africa.com/isdasoil/v2/point
  ?lat={lat}&lon={lon}&depth=0-20&properties=N_tot,ph,P_tot,K_tot,C_tot,SOC
  Authorization: Bearer {key}
```

## Twilio (WhatsApp + SMS)

### WhatsApp Text
```python
client.messages.create(
    from_=f"whatsapp:{WHATSAPP_NUMBER}",
    to=f"whatsapp:{farmer_phone}",
    body=text
)
```

### WhatsApp Audio
```python
client.messages.create(
    from_=f"whatsapp:{WHATSAPP_NUMBER}",
    to=f"whatsapp:{farmer_phone}",
    media_url=[audio_url]
)
```

### SMS (Critical Alerts)
```python
client.messages.create(
    from_=TWILIO_PHONE_NUMBER,
    to=farmer_phone,
    body=alert_text
)
```

## Masumi (Cardano Decision Logging)
```python
from masumi_sdk import MasumiAgentSigner, CardanoLedgerClient

signer = MasumiAgentSigner(secret_key=MASUMI_SECRET_KEY)
ledger = CardanoLedgerClient(network="preprod")

signed = signer.sign_payload(decision_payload)
tx_hash = ledger.submit_compliance_record(
    did="did:masumi:cardano:agent_diag_01",
    payload_hash=signed.hash,
    signature=signed.signature
)
```
